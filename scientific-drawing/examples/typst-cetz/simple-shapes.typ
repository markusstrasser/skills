#import "@preview/cetz:0.2.2": canvas, draw

#set page(width: 15cm, height: 15cm)

= CeTZ Simple Shapes Example

#canvas({
  import draw: *

  // Circle with fill
  circle((0, 0), radius: 1, fill: blue.lighten(80%), stroke: blue)

  // Line with arrow
  line((0, 2), (3, 2), stroke: green, mark: (end: ">"))

  // Content labels
  content((0, 0), [Circle])
  content((1.5, 2.3), [Arrow])
})
