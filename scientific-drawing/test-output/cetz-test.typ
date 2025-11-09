
#import "@preview/cetz:0.2.2": canvas, draw

#canvas({
  import draw: *

  circle((0, 0), radius: 1, fill: blue.lighten(80%))
  line((0, 0), (2, 1), stroke: red)
  content((1, 0.5), [Test])
})
