# Claude Code Instructions

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md

## MCP Tool Mandates

### ALWAYS Use These MCPs

1. **Context7 MCP - Dependency Management**
   - ALWAYS use Context7 MCP before installing or updating any dependencies
   - ALWAYS check latest versions and best practices with Context7
   - Example: Before adding Tailwind, check Context7 for current config approach (no tailwind.config.js in latest versions)
   - NEVER install packages without consulting Context7 first

2. **v0.dev - Layout and Page Design**
   - ALWAYS use v0 for creating page layouts and overall design structure
   - Use v0 for responsive design patterns and grid layouts
   - Let v0 generate initial component structure for pages

3. **Kibo UI MCP - Component Design**
   - ALWAYS use Kibo UI MCP for individual UI component design and generation
   - Use Kibo for forms, buttons, cards, modals, and interactive elements
   - Leverage Kibo for shadcn/ui component customization

### Workflow
```
Need dependency → Context7 MCP → Get latest version/best practices → Install
Need page layout → v0.dev → Generate structure → Implement
Need UI component → Kibo UI MCP → Generate component → Integrate
```

## Package Manager

### ALWAYS Use pnpm

- **NEVER** use `npm` for package management
- **ALWAYS** use `pnpm` for all package operations
- This project uses pnpm exclusively for dependency management

#### Common Commands
```bash
pnpm install              # Install dependencies (NOT npm install)
pnpm add <package>        # Add a package (NOT npm install <package>)
pnpm remove <package>     # Remove a package (NOT npm uninstall)
pnpm run <script>         # Run a script (NOT npm run)
pnpm dlx <command>        # Execute a package (NOT npx)
```

#### Why pnpm?
- Efficient disk space usage through content-addressable storage
- Strict dependency resolution prevents phantom dependencies
- Faster installation times
- Better monorepo support
