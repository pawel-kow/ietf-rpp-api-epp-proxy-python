# Documentation maintenance

- **Docs change with the code.** Any change to an interface, structure, flow or
  convention updates the affected docs in the same change. A change is not
  complete until the docs match the code.
- **Every edit lands in the right place (standing rule).** This applies to all
  future edits of `Agents.md` and `docs/agents/`. `Agents.md` and `<area>.md` must
  stay usable as-is in any project. Names, commands, paths and domain terms of this
  project go in `<area>.project.md`. A rule with both parts is split: the principle
  goes in the generic file, the specifics in the project file. **If unsure whether
  a rule is generic or project-specific, ask the user.**
- **One home per fact.** Link to it rather than repeating it.
- **Keep the entry file short.** `Agents.md` carries only the working agreement and
  the documentation map. Content for one area belongs in that area's file.
- **New areas are added to the map** in `Agents.md` in the same change.
- **Keep known-debt lists current.** Every entry links its GitHub issue. Remove an
  entry in the change that fixes it.
