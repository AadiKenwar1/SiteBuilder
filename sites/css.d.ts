// Ambient declaration so side-effect CSS imports (`import "./styles.css"`)
// typecheck. The Next plugin handles the actual bundling; this only satisfies the
// type checker under the pinned TypeScript.
declare module "*.css"
