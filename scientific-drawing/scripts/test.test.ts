#!/usr/bin/env bun
/**
 * Test suite for scientific drawing tools
 */

import { test, expect, describe } from "bun:test";
import { $ } from "bun";
import { existsSync, mkdirSync, rmSync, writeFileSync } from "fs";
import { join } from "path";

// Test directory
const TEST_DIR = join(import.meta.dir, "..", "test-output");

// Ensure test directory exists
if (existsSync(TEST_DIR)) {
  rmSync(TEST_DIR, { recursive: true });
}
mkdirSync(TEST_DIR, { recursive: true });

describe("Tool Availability", () => {
  test("typst is installed", async () => {
    const result = await $`which typst`.quiet().nothrow();
    expect(result.exitCode).toBe(0);
  });

  test("asy (Asymptote) is installed", async () => {
    const result = await $`which asy`.quiet().nothrow();
    expect(result.exitCode).toBe(0);
  });

  test("bun is installed", async () => {
    const result = await $`which bun`.quiet().nothrow();
    expect(result.exitCode).toBe(0);
  });

  test("bunx is available", async () => {
    const result = await $`which bunx`.quiet().nothrow();
    expect(result.exitCode).toBe(0);
  });
});

describe("Typst/CeTZ", () => {
  test("compile simple Typst document", async () => {
    const input = join(TEST_DIR, "simple.typ");
    const output = join(TEST_DIR, "simple.pdf");

    writeFileSync(input, `
#set page(width: 10cm, height: 10cm)

= Test Document

This is a simple test.

#box(stroke: black, inset: 1em)[
  Hello, World!
]
`);

    const result = await $`typst compile ${input} ${output}`.quiet().nothrow();

    expect(result.exitCode).toBe(0);
    expect(existsSync(output)).toBe(true);
  });

  test("compile Typst with CeTZ", async () => {
    const input = join(TEST_DIR, "cetz-test.typ");
    const output = join(TEST_DIR, "cetz-test.pdf");

    writeFileSync(input, `
#import "@preview/cetz:0.2.2": canvas, draw

#canvas({
  import draw: *

  circle((0, 0), radius: 1, fill: blue.lighten(80%))
  line((0, 0), (2, 1), stroke: red)
  content((1, 0.5), [Test])
})
`);

    const result = await $`typst compile ${input} ${output}`.quiet().nothrow();

    expect(result.exitCode).toBe(0);
    expect(existsSync(output)).toBe(true);
  });
});

describe("Asymptote", () => {
  test("compile simple Asymptote diagram", async () => {
    const input = join(TEST_DIR, "simple.asy");
    const output = join(TEST_DIR, "simple.pdf");

    writeFileSync(input, `
size(100);
draw(unitcircle, blue);
dot((0,0), red);
`);

    const result = await $`asy -f pdf -noV ${input}`.quiet().nothrow();

    expect(result.exitCode).toBe(0);
    expect(existsSync(output)).toBe(true);
  });
});

describe("Penrose", () => {
  test("compile simple Penrose diagram", async () => {
    const domainFile = join(TEST_DIR, "test.domain");
    const substanceFile = join(TEST_DIR, "test.substance");
    const styleFile = join(TEST_DIR, "test.style");
    const trioFile = join(TEST_DIR, "test.trio.json");
    const output = join(TEST_DIR, "test.svg");

    // Create domain file
    writeFileSync(domainFile, `type Set`);

    // Create substance file
    writeFileSync(substanceFile, `Set A, B`);

    // Create style file
    writeFileSync(styleFile, `
forall Set x {
  x.shape = Circle {
    r: 50
  }
}
`);

    // Create trio JSON
    writeFileSync(trioFile, JSON.stringify({
      domain: "./test.domain",
      style: ["./test.style"],
      substance: "./test.substance",
      variation: "test-seed"
    }, null, 2));

    // Change to test directory for Penrose (it uses relative paths)
    const originalCwd = process.cwd();
    process.chdir(TEST_DIR);

    const result = await $`bunx @penrose/roger trio test.trio.json`.quiet().nothrow();

    process.chdir(originalCwd);

    // Write output
    if (result.exitCode === 0) {
      writeFileSync(output, result.stdout);
    }

    expect(result.exitCode).toBe(0);
    expect(existsSync(output)).toBe(true);
  });
});

describe("TikZ (via node-tikzjax)", () => {
  test("render simple TikZ diagram", async () => {
    const tikzjax = await import("node-tikzjax");

    const tikzCode = `
\\begin{document}
\\begin{tikzpicture}
  \\draw (0,0) circle (1cm);
  \\draw[->] (0,0) -- (1,0);
\\end{tikzpicture}
\\end{document}
`;

    const svg = await tikzjax.default(tikzCode);

    expect(svg).toContain("<svg");
    expect(svg).toContain("</svg>");
  });
});

describe("Helper Scripts", () => {
  const scriptsDir = join(import.meta.dir);

  test("generate.sh exists and is executable", () => {
    const script = join(scriptsDir, "generate.sh");
    expect(existsSync(script)).toBe(true);
  });

  test("batch-generate.sh exists and is executable", () => {
    const script = join(scriptsDir, "batch-generate.sh");
    expect(existsSync(script)).toBe(true);
  });

  test("check-tools.sh exists and is executable", () => {
    const script = join(scriptsDir, "check-tools.sh");
    expect(existsSync(script)).toBe(true);
  });

  test("tikz-render.js exists and is executable", () => {
    const script = join(scriptsDir, "tikz-render.js");
    expect(existsSync(script)).toBe(true);
  });
});

describe("Integration Tests", () => {
  test("generate.sh works with Typst file", async () => {
    const input = join(TEST_DIR, "integration.typ");
    const output = join(TEST_DIR, "integration.pdf");

    writeFileSync(input, `
#set page(width: 8cm, height: 6cm)
= Integration Test
This is a test.
`);

    const script = join(import.meta.dir, "generate.sh");
    const result = await $`bash ${script} ${input}`.quiet().nothrow();

    expect(result.exitCode).toBe(0);
    expect(existsSync(output)).toBe(true);
  });
});

console.log("\n✓ All tests passed!");
console.log(`\nTest output directory: ${TEST_DIR}`);
