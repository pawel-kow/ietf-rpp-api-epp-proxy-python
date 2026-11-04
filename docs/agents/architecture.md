# Architecture and coding rules

Project-agnostic rules, binding for all new code. The system's actual structure
and its known debt are in [architecture.project.md](architecture.project.md).

**Known debt.** Where current code violates a rule, the violation is listed as
known debt in the project file. Never copy a known-debt pattern into new code and
never let the debt grow. Do not fix debt as a side effect of unrelated work.

## Structure and dependencies

1. **One class per file.** Package init files contain only re-exports, never
   implementation.
2. **No imports inside function or method bodies.** All imports sit at module
   level. The only accepted exception is a conditional startup-time import that
   avoids a circular dependency, documented with a comment.
3. **Dependencies point downward only.** Sibling entry-point modules never import
   from each other, and no code imports another package's private names. Shared
   logic gets its own module.
4. **Business logic is framework-free; handlers are thin presenters.** Multi-step
   flows do not live inside route handlers, do not import the web framework, and
   exist exactly once. Presentation variants differ only in how they render the
   flow's typed results and errors.

## Same pattern for the same thing

5. **The same kind of thing is always done the same way.** One config-loading
   path, one error-mapping path per error family, one response-construction style
   per surface, one name per concept. When touching code that deviates, converge
   it to the canonical pattern rather than adding a competing variant.
6. **Repeated orchestration is encapsulated, never copied.** If a multi-step
   orchestration would appear at a second call site, first move it into its own
   module. A second hand-written copy is forbidden, a third is a defect.
7. **Cross-cutting guards are written once** (decorator, middleware or equivalent),
   never copy-pasted per handler.
