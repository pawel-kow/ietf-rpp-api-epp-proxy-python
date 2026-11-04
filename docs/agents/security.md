# Security

Project-agnostic rules. Project invariants and known debt are in
[security.project.md](security.project.md).

- **Secrets stay out of version control.** Credentials are read from the
  environment or an untracked configuration, never committed.
- **Secrets stay out of logs.** Never log credentials, tokens or complete messages
  that can contain them.
- **No internal detail in client responses.** Raw exception text, stack traces and
  backend internals never reach clients.
- **Validate input at the boundary** before it reaches business logic.
- **Escape at the output boundary.** Values placed into XML, HTML, SQL, shell
  commands or any other structured format go through that format's escaping or
  builder, never string interpolation.
- **Protections are invariants.** A change must preserve existing security
  controls. Weakening one needs an explicit, reviewed decision.
