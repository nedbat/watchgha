########################
Watch GitHub Action runs
########################

This package provides one command, ``watch_gha_runs``.  It takes a GitHub repo
URL and a branch name, and displays the status of the latest GitHub Action runs
on that branch.  If any of the runs are in progress, it will refresh the
display each second with the current status.

If you like, the name can be pronounced, "Watching? Ha!"


Installation
============

I suggest installing with `pipx`_:

.. code-block:: shell

    $ pipx install git+https://github.com/nedbat/watchgha

Now you have a command ``watch_gha_runs`` available.  I use a `git alias`_
so that my current repo and branch are implied:

.. code-block:: ini

    [alias]
        runs = "!f() { \
            watch_gha_runs \
                \"$(git remote get-url origin)\" \
                \"$(git rev-parse --abbrev-ref HEAD)\"; \
        }; f"

Now ``git runs`` will show a live display of the current runs on your branch.

You can authenticate against GitHub if needed using either an entry in your
.netrc file, or by setting the ``GITHUB_TOKEN`` environment variable.


Display
=======

The output shows runs and jobs.  The current step of each job is shown, with a
row of bullets indicating the number of steps, and which is current:

.. image:: https://nedbatchelder.com/pix/watchgha.png

.. code-block::

    fix: recent pypy3.9 now omits lines after jumps nedbat/fix-pypy-nightly    53923268e8f9  @08:32am
    ⏲ queued       Tests             view 4397455341
        3.7 on ubuntu                  ↻ •••••••• Run tox for 3.7
        3.8 on ubuntu                  ↻ •••••••• Run tox for 3.8
        3.9 on ubuntu                  ↻ •••••••• Run tox for 3.9
        3.10 on ubuntu                 ↻ •••••••• Run tox for 3.10
        3.11 on ubuntu                 ↻ •••••••• Run tox for 3.11
        pypy-3.7 on ubuntu             ↻ •••••••• Run tox for pypy-3.7
        pypy-3.9 on ubuntu             ↻ •••••••• Run tox for pypy-3.9
        3.7 on macos                   ↻ •••••••• Run tox for 3.7
        3.8 on macos                   ↻ •••••••• Run tox for 3.8
        3.9 on macos                   ⏲ queued
        3.10 on macos                  ↻ •••••••• Run tox for 3.10
        3.11 on macos                  ↻ •••••••• Run tox for 3.11
        pypy-3.7 on macos              ⏲ queued
        pypy-3.9 on macos              ⏲ queued
        3.7 on windows                 ⏲ queued
        3.8 on windows                 ⏲ queued
        3.9 on windows                 ⏲ queued
        3.10 on windows                ↻ ••••••• Check out the repo
        3.11 on windows                ⏲ queued
        pypy-3.7 on windows            ⏲ queued
    ↻ in_progress  Quality            view 4397455342
        Check types                    ✓ success
        Build docs                     ↻ ••••••• Tox doc
        Pylint etc                     ↻ ••••••• Tox lint
    ↻ in_progress  Python Nightly Tests   view 4397455346
        Python 3.10-dev                ↻ •••◦•••• Run tox
        Python 3.11-dev                ↻ •••◦•••• Run tox
        Python 3.12-dev                ↻ •••◦•••• Run tox
        Python pypy-3.7-nightly        ↻ ••◦•••••• Run tox
        Python pypy-3.8-nightly        ↻ ••◦•••••• Run tox
        Python pypy-3.9-nightly        ↻ ••◦•••••• Run tox

Jobs and runs are collapsed once all of their children are successful::

    fix: recent pypy3.9 now omits lines after jumps nedbat/fix-pypy-nightly    53923268e8f9  @08:32am
    ✓ success      Tests              view 4397455341
    ↻ in_progress  Quality            view 4397455342
        Check types                    ✓ success
        Build docs                     ↻ ••••••• Tox doc
        Pylint etc                     ✓ success
    ✗ failure      Python Nightly Tests   view 4397455346
        Python 3.10-dev                ✓ success
        Python 3.11-dev                ✓ success
        Python 3.12-dev                ✓ success
        Python pypy-3.7-nightly        ✓ success
        Python pypy-3.8-nightly        ✓ success
        Python pypy-3.9-nightly        ✗ failure Run tox

Once all the runs are completed, the command ends, displaying the final
status::

    fix: recent pypy3.9 now omits lines after jumps nedbat/fix-pypy-nightly [push]   53923268e8f9  @08:32am
    ✓ success      Tests              view 4397455341
    ✓ success      Quality            view 4397455342
    ✗ failure      Python Nightly Tests   view 4397455346
        Python 3.10-dev                ✓ success
        Python 3.11-dev                ✓ success
        Python 3.12-dev                ✓ success
        Python pypy-3.7-nightly        ✓ success
        Python pypy-3.8-nightly        ✓ success
        Python pypy-3.9-nightly        ✗ failure Run tox


Changelog
=========

Unreleased
----------

- Runs can be selected by a commit SHA by using ``--sha`` on the command line.

- Retry if GitHub returns "502 - Bad Gateway".


0.5.0 – 2023-03-15
------------------

- Uses a ``GITHUB_TOKEN`` environment variable for authentication if it is
  defined.


0.0.2 – 2023-03-14
------------------

- Support more forms of repo URLs: ``git@github.com:``, without ``.git``, etc.

- Better error messages if the repo URL can't be parsed.


0.0.1 – 2023-03-13
------------------

First version


Development
===========

The code is a bit messy and undocumented, and there are no tests.  If you want
to change the code, open an issue and let's talk about it.

Contributors:

- Ned Batchelder
- Hugo van Kemenade


Back Story
==========

This started as a formatter for the output of ``gh run list`` from the `gh
run command`_.  Then I tried ``gh run watch``, but wasn't happy with its
choices. So I wrote my own.

.. _gh run command: https://cli.github.com/manual/gh_run
.. _git alias: https://www.atlassian.com/git/tutorials/git-alias
.. _pipx: https://pypi.org/project/pipx/
