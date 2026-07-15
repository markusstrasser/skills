// Simple Asymptote example with shapes and labels
size(200);

// Draw a circle
draw(unitcircle, blue + linewidth(1.5));

// Draw some lines
draw((0,0)--(1,0), red, Arrow);
draw((0,0)--(0,1), green, Arrow);

// Add labels
label("$x$", (1,0), E, red);
label("$y$", (0,1), N, green);
label("Unit Circle", (0,-1.3), S, blue);

// Add a filled dot at origin
dot((0,0), red + linewidth(5));
label("Origin", (0,0), NW);
