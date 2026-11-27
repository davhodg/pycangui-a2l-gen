# Security policy

## Reporting a vulnerability

Please report it privately rather than in a public issue:
**[report a vulnerability](https://github.com/davhodg/pycangui-a2l-gen/security/advisories/new)**,
which is also under the repository's *Security* tab. Say what you found, how to make it
happen, and which version of the plugin and of pycangui you were running.

One that is in pycangui rather than in this plugin goes to
[pycangui's security policy](https://github.com/davhodg/pycangui/security/policy), whose
rules apply here too: no promised response time, every report read and answered, and the
fix and the advisory published together.

## Versions that get fixes

The latest release and `main`.

## What is and is not a vulnerability

The plugin runs a2ltool, which it carries, on files you choose, and writes the A2L you ask
for. What **is** worth reporting: it running anything other than its own a2ltool, reading or
writing a file nobody chose, or an A2L it writes that differs from what a2ltool produced.

A problem in a2ltool itself goes to [a2ltool](https://github.com/DanielT/a2ltool); say here
too if the plugin is what exposes it.
