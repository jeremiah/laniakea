# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2022 Matthias Klumpp <matthias@tenstral.net>
#
# SPDX-License-Identifier: LGPL-3.0+

import sys

import rich
import click
from rich.table import Table
from rich.prompt import Confirm
from rich.console import Console

import laniakea.typing as T
from laniakea import LocalConfig
from laniakea.db import (
    BinaryPackage,
    SourcePackage,
    ArchiveRepoSuiteSettings,
    session_scope,
)
from laniakea.archive import remove_source_package


@click.command('ls')
@click.option(
    '--repo',
    'repo_name',
    default=None,
    help='Name of the repository to act on, if not set all repositories will be checked',
)
@click.option(
    '--suite',
    '-s',
    'suite_name',
    default=None,
    help='Name of the suite to act on, if not set all suites will be processed',
)
@click.argument('term', nargs=1)
def list(term: str, repo_name: T.Optional[str], suite_name: T.Optional[str]):
    """List repository packages."""

    term_q = '%' + term + '%'
    with session_scope() as session:
        # find source packages
        spkg_q = session.query(SourcePackage).filter(SourcePackage.name.like(term_q))
        if repo_name:
            spkg_q = spkg_q.filter(SourcePackage.repo.has(name=repo_name))
        if suite_name:
            spkg_q = spkg_q.filter(SourcePackage.suite.has(name=suite_name))
        spkgs = spkg_q.all()

        # find binary packages
        bpkg_q = session.query(BinaryPackage).filter(BinaryPackage.name.like(term_q))
        if repo_name:
            bpkg_q = spkg_q.filter(BinaryPackage.repo.has(name=repo_name))
        if suite_name:
            bpkg_q = spkg_q.filter(BinaryPackage.suite.has(name=suite_name))
        bpkgs = bpkg_q.all()

        if not spkgs and not bpkgs:
            click.echo('Nothing found.', err=True)
            sys.exit(2)

        table = Table(box=rich.box.MINIMAL)
        table.add_column('Package', no_wrap=True)
        table.add_column('Version', style='magenta', no_wrap=True)
        table.add_column('Repository')
        table.add_column('Suites')
        table.add_column('Component')
        table.add_column('Architectures')

        for spkg in spkgs:
            table.add_row(
                spkg.name,
                spkg.version,
                spkg.repo.name,
                ' '.join([s.name for s in spkg.suites]),
                spkg.component.name,
                'source',
            )
        for bpkg in bpkgs:
            table.add_row(
                bpkg.name,
                bpkg.version,
                bpkg.repo.name,
                ' '.join([s.name for s in bpkg.suites]),
                bpkg.component.name,
                bpkg.architecture.name,
            )

        console = Console()
        console.print(table)


def print_package_details(spkgs: T.List[SourcePackage]):
    table = Table(box=rich.box.MINIMAL)
    table.add_column('Package', no_wrap=True)
    table.add_column('Version', style='magenta', no_wrap=True)
    table.add_column('Repository')
    table.add_column('Suites')
    table.add_column('Component')
    table.add_column('Binaries')

    for spkg in spkgs:
        table.add_row(
            spkg.name,
            spkg.version,
            spkg.repo.name,
            ' '.join([s.name for s in spkg.suites]),
            spkg.component.name,
            ' '.join([b.name for b in spkg.binaries]),
        )

    console = Console()
    console.print(table)


@click.command('remove')
@click.option(
    '--repo',
    'repo_name',
    default=None,
    help='Name of the repository to act on, if not set the default repository will be used.',
)
@click.option(
    '--suite',
    '-s',
    'suite_name',
    required=True,
    help='Name of the suite to act on.',
)
@click.argument('source_pkgname', nargs=1)
def remove(source_pkgname: str, repo_name: T.Optional[str], suite_name: str):
    """Delete a source package (and its binaries) from a suite in a repository."""

    if not repo_name:
        lconf = LocalConfig()
        repo_name = lconf.master_repo_name

    with session_scope() as session:
        rss = (
            session.query(ArchiveRepoSuiteSettings)
            .filter(
                ArchiveRepoSuiteSettings.repo.has(name=repo_name), ArchiveRepoSuiteSettings.suite.has(name=suite_name)
            )
            .one_or_none()
        )

        if not rss:
            click.echo('Suite {} not found in repository {}.'.format(suite_name, repo_name), err=True)
            sys.exit(2)

        spkgs = (
            session.query(SourcePackage)
            .filter(
                SourcePackage.repo_id == rss.repo_id,
                SourcePackage.suites.any(id=rss.suite_id),
                SourcePackage.name == source_pkgname,
            )
            .all()
        )

        if not spkgs:
            click.echo('Package {} not found in repository {}/{}.'.format(source_pkgname, repo_name, suite_name))
            sys.exit(0)

        print_package_details(spkgs)
        remove_confirmed = Confirm.ask('Do you really want to delete these packages?', default=False)

        if remove_confirmed:
            for spkg in spkgs:
                remove_source_package(session, rss, spkg)