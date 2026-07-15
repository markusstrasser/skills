#!/usr/bin/env bun
/**
 * Render TikZ diagrams to SVG using node-tikzjax
 */

import { readFileSync } from 'fs';

const main = async () => {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.error('Usage: tikz-render.js <input.tikz.tex>');
    console.error('');
    console.error('Renders TikZ code to SVG output (stdout)');
    process.exit(1);
  }

  const inputFile = args[0];

  try {
    // Dynamically import tikzjax
    const tikzModule = await import('node-tikzjax');

    // Initialize TikZ
    await tikzModule.load();

    // Read TikZ source
    const tikzCode = readFileSync(inputFile, 'utf-8');

    // Render to SVG
    const svg = await tikzModule.tex(tikzCode, {});

    // Output to stdout or file
    if (args[1]) {
      const { writeFileSync } = await import('fs');
      writeFileSync(args[1], svg);
      console.error(`SVG written to ${args[1]}`);
    } else {
      console.log(svg);
    }

  } catch (error) {
    console.error(`Error rendering TikZ: ${error.message}`);
    console.error(error.stack);
    process.exit(1);
  }
};

main();
