| |kit| |versions|
| |sponsor| |mastodon-nedbat| |bluesky-nedbat|

########################
Watch GitHub Action runs
########################

This package provides one command, ``watch_gha_runs``.  It displays the status
of the latest GitHub Action runs on your current branch.  If any of the runs
are in progress, it will refresh the display repeatedly with the latest status.

If you like, the name can be pronounced, "Watching? Ha!"


Installation
============

I suggest installing with `pipx`_:

.. code-block:: shell

    $ pipx install watchgha

Now you have a command ``watch_gha_runs`` available.  It will check all GitHub
remotes for the current directory's repo, and find action runs for the current
branch.

For complex defaulting, you can use a `git alias`_.  For example, this provides
similar defaults, but can be adapted:

.. code-block:: ini

    [alias]
        runs = "!f() { \
            watch_gha_runs $@ \
                \"$(git remote get-url origin)\" \
                \"$(git rev-parse --abbrev-ref HEAD)\"; \
        }; f"

Now ``git runs`` will show a live display of the current runs on your branch.

You can authenticate against GitHub if needed using either an entry in your
.netrc file, or by setting the ``GITHUB_TOKEN`` environment variable.

No authentication is needed for public repos.  For private repos, OAuth or
classic tokens need the ``repo`` scope, and fine-grained tokens need the
"Actions (read)" repository permission.

If you use GitHub Enterprise, you can set the environment variables
``GITHUB_SERVER_URL`` (default: ``https://github.com``) and
``GITHUB_API_URL`` (default: ``https://api.github.com``)
to match your instance.

Usage
=====

.. [[[cog
    import os
    import subprocess
    import textwrap
    command = "watch_gha_runs --help".split()
    env = dict(os.environ, COLUMNS="72")
    output = subprocess.check_output(command, env=env)
    print()
    print(".. code-block::")
    print()
    print("    $", *command)
    print(textwrap.indent(output.decode(), "    "))
.. ]]]

.. code-block::

    $ watch_gha_runs --help
    Usage: watch_gha_runs [OPTIONS] [REPO] [BRANCH]

      Watch GitHub Action runs.

      Repeatedly gets the latest status and redraws the screen, until all
      of the jobs are complete.

      REPO is a local directory or GitHub URL, defaulting to ".".

      BRANCH is defaulted from the git repo.

    Options:
      --sha TEXT                The commit SHA to use. Must be a full SHA.
      --poll INTEGER            How many seconds between refreshes.
                                [default: 15]
      --wait, --wait-for-start  Wait for jobs to start.
      --only TEXT               Words to limit the workflows shown. Only
                                workflows with these comma separated case
                                insensitive substrings in their names will
                                be shown.
      --message TEXT            A message to display at the top of the
                                screen.
      --help                    Show this message and exit.

.. [[[end]]] (sum: 9LxE5cjkve)


Display
=======

The output shows runs and jobs.  The current step of each job is shown, with a
row of bullets indicating the number of steps, and which is current:

..
    How to make the animated gif:
      - https://github.com/asciinema/agg; brew install agg
      - branch in coverage.py
      - comment out python versions in testsuite.yml to have five.
      - commit as "fix: most awesome fix"
      create window 80x24
      $ g ampf; asciinema rec --overwrite watch.cast --command "watch_gha_runs --wait-for-start --poll=5"
      $ agg --speed=10 --font-family="Monego,Symbola" --font-size=18 watch.cast --renderer=fontdue watch.gif

.. image:: https://raw.githubusercontent.com/nedbat/watchgha/main/watch.gif

(This is sped up, watch_gha_runs won't make your GitHub actions run faster!)

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

.. Release process:
    - Use `make check_release` to see if everything is ready for a release.
    - This changelog is updated manually, not with scriv.
    - Bump the version in src/watchgha/__init__.py
    - Comments are added manually to GitHub issues and pull requests.
    - Use `make release` to release a new version.

.. scriv-start-here

2.6.0 – 2025-12-29
------------------

- Progress is displayed in the terminal with OSC 9;4 escape sequences.


2.5.0 – 2025-12-13
------------------

- A new option ``--message`` lets you provide a line of text to display at the
  top of the output.

- The option ``--wait-for-start`` can now be shortened tp ``--wait``,
  implementing the good idea from `issue 27`_.

.. _issue 27: https://github.com/nedbat/watchgha/issues/27

2.4.2 – 2025-10-20
------------------

- Corrected a test that used a hardcoded date, derp.

- Declared support for Python 3.14.

2.4.1 – 2025-03-26
------------------

- Printed data now has control characters scrubbed, to prevent extremely
  unlikely terminal attacks.

- Oops, it didn't work on Python 3.9, now fixed.

2.4.0 – 2025-03-25
------------------

- GitHub no longer reports jobs in the same nice order as their UI shows, so
  now we sort them by name.  This isn't the same order as the UI, but is more
  understandable than the random order returned by the API.

- Dropped support for Python 3.7 and 3.8.

2.3.2 – 2024-06-23
------------------

- GITHUB_SERVER_URL's like "git@git.mydomain.com" are now correctly parsed,
  closing `issue 22`_.

- Added a stop sign emoji for jobs in the Waiting state.

- Most fatal errors now result in a status code of 1. It was mistakenly 2.

.. _issue 22: https://github.com/nedbat/watchgha/issues/22


2.3.1 – 2024-05-25
------------------

- Workflows with many jobs could be truncated.  There is still a limit of 100
  jobs, but that is better than the earlier limit of 30.


2.3.0 – 2024-04-10
------------------

- GitHub Enterprise is supported via ``GITHUB_SERVER_URL`` and
  ``GITHUB_API_URL`` environment variables.
  Thanks, `Colin Marquardt <pull 21_>`_.

- Fix: in unusual cases, GitHub can return strange statuses for job steps.
  Those are now displayed as question marks.

.. _pull 21: https://github.com/nedbat/watchgha/pull/21


2.2.2 – 2024-02-03
------------------

- Fix: steps can be in a "pending" state, and are now displayed with a dot
  instead of "pending".


2.2.1 – 2024-01-14
------------------

- Fix: don't fail if a .netrc file can't be found. Fixes `issue 18`_.

- Fix: in the odd case of duplicate remotes, don't list workflow runs twice.
  Fixes `issue 19`_.

.. _issue 18: https://github.com/nedbat/watchgha/issues/18
.. _issue 19: https://github.com/nedbat/watchgha/issues/19


2.2.0 — 2024-01-11
------------------

- Now all GitHub remotes are checked for jobs.  Previously, only one was
  checked, so you wouldn't see jobs running on an upstream fork.

- Added option ``--only`` to limit which workflows are displayed as requested
  in `issue 17`_.

- The output is now redrawn immediately when the terminal window is resized (on
  Mac or Linux).  Thanks, `Bill Mill <pull 14_>`_.

.. _pull 14: https://github.com/nedbat/watchgha/pull/14
.. _issue 17: https://github.com/nedbat/watchgha/issues/17


2.1.1 — 2023-07-05
------------------

- Implicit .netrc authentication stopped working, but has been fixed. Thanks,
  `Rob Weir <pull 11_>`_.

.. _pull 11: https://github.com/nedbat/watchgha/pull/11


2.0.0 — 2023-07-02
------------------

- The default polling interval is now 15 seconds.

- Now the GitHub repo location and branch name are defaulted from the current
  git repo.  The repo location can be a local directory or GitHub URL. Closes
  `issue 7`_.

- A new option, ``--wait-for-start`` will make watch_gha_runs wait until jobs
  are in progress.  This fixes a problem with using watch_gha_runs
  programmatically: it can check the run status before any new runs have
  started, and simply report the done state of the last bunch of runs, then
  quit.

- Fix: if a .yml workflow file couldn't be parsed, its "run" would persist in
  the list of runs for longer than it should.  Now those unparsable runs aren't
  displayed at all.

- Fix: skipped runs are considered finished, and don't need their jobs shown.

- Error reporting is improved, removing unneeded noisy tracebacks in some
  cases, and providing more information for GitHub API errors.
  Closes `issue 8`_.

- More operations are retried on failure, fixing `issue 10`_.

- Interrupting with ctrl-C will set the exit status to 2.

.. _issue 7: https://github.com/nedbat/watchgha/issues/7
.. _issue 8: https://github.com/nedbat/watchgha/issues/8
.. _issue 10: https://github.com/nedbat/watchgha/issues/10


1.0.0 — 2023-04-15
------------------

- The ``--poll`` option sets the number of seconds to wait between refreshes.

- Requests to GitHub are now made asynchronously, speeding execution.

- Redirections from GitHub (for example, if a repo is renamed or moved) are
  followed transparently.

- The exit code is now 1 if any runs failed, 0 if all were successful.

- Long lines are no longer wrapped too short.


0.6.0 — 2023-03-22
------------------

- Runs can be selected by a commit SHA by using ``--sha`` on the command line.

- Retry if GitHub returns "502 - Bad Gateway".


0.5.0 — 2023-03-15
------------------

- Uses a ``GITHUB_TOKEN`` environment variable for authentication if it is
  defined.


0.0.2 — 2023-03-14
------------------

- Support more forms of repo URLs: ``git@github.com:``, without ``.git``, etc.

- Better error messages if the repo URL can't be parsed.


0.0.1 — 2023-03-13
------------------

First version


.. scriv-end-here

Development
===========

The code is a bit messy and undocumented.  If you want
to change the code, open an issue and let's talk about it.

To run tests::

    $ make tools
    $ make test

Contributors:

- Ned Batchelder
- Bill Mill
- Hugo van Kemenade
- Rob Weir


Back Story
==========

This started as a formatter for the output of ``gh run list`` from the `gh
run command`_.  Then I tried ``gh run watch``, but wasn't happy with its
choices. So I wrote my own.

.. _gh run command: https://cli.github.com/manual/gh_run
.. _git alias: https://www.atlassian.com/git/tutorials/git-alias
.. _pipx: https://pypi.org/project/pipx/

.. |kit| image:: https://img.shields.io/pypi/v/watchgha
    :target: https://pypi.org/project/watchgha/
    :alt: PyPI status
.. |versions| image:: https://img.shields.io/pypi/pyversions/watchgha.svg?logo=python&logoColor=FBE072
    :target: https://pypi.org/project/watchgha/
    :alt: Python versions supported
.. |license| image:: https://img.shields.io/pypi/l/watchgha.svg
    :target: https://pypi.org/project/watchgha/
    :alt: License
.. |sponsor| image:: https://img.shields.io/badge/%E2%9D%A4-Sponsor%20me-brightgreen?style=flat&logo=GitHub
    :target: https://github.com/sponsors/nedbat
    :alt: Sponsor me on GitHub
.. |bluesky-nedbat| image:: https://img.shields.io/badge/dynamic/json?style=flat&color=96a3b0&labelColor=3686f7&logo=icloud&logoColor=white&label=@nedbat&url=https%3A%2F%2Fpublic.api.bsky.app%2Fxrpc%2Fapp.bsky.actor.getProfile%3Factor=nedbat.com&query=followersCount
    :target: https://bsky.app/profile/nedbat.com
    :alt: nedbat on Bluesky
.. |mastodon-nedbat| image:: https://img.shields.io/badge/dynamic/json?style=flat&labelColor=450657&logo=mastodon&logoColor=ffffff&label=@nedbat&query=followers_count&url=https%3A%2F%2Fhachyderm.io%2Fapi%2Fv1%2Faccounts%2Flookup%3Facct=nedbat
    :target: https://hachyderm.io/@nedbat
    :alt: nedbat on Mastodon
