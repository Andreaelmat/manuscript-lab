# Security

Manuscript Lab is a local editorial skill. It has no accounts, no service, and no network client of its own.

## What the scripts do

The Python scripts use the standard library. They read a manuscript and write JSON or Markdown beside it, in a directory you choose. They do not send the manuscript anywhere. They refuse a DOCX that declares a document type or an XML entity, and they do not execute manuscript text.

An agent that follows the skill may still send the manuscript to its own model provider. That traffic follows the agent's settings and the provider's terms. Installing this skill does not keep a manuscript on your machine only.

## What to keep out of the repository

Do not commit manuscripts, reviews of private works, indexes or extracts of those works, credentials, tokens, or absolute paths that identify a person or a private file. Example output that is checked in should use a path relative to the repository.

## Reporting a vulnerability

If you find a problem in how the scripts handle untrusted manuscript files, use the private vulnerability reporting on this GitHub repository once it exists. Please include the script, the input shape, and the effect. Do not include a private manuscript. A quotation long enough to reproduce a parser bug is enough.

There is no bounty program.
