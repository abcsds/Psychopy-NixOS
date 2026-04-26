# Dual Task

Task for dual attention paradigm. Task 1 is a cursor persecution task and task 2 is a Go-NoGo task. Designed for Psychopy (2024.1.5). Requires pointer device (mouse suggested).

## Parameters

Motion of task 1 target has 20% chance of direction change on every frame. Probability of task 2 target deppends on proportion between  ammount of all non-target letters `all_letters` and the target multiplier `n_x`. Time of next target is a normal distribution centered at `between_stimuli` +/- 1 sec.

```python
circle_radius = 10
circle_speed = 15
angle_uncertainty = math.pi/2 # +/- 90 degrees
cross_color = "white"
stimulus_duration = 0.5
between_stimuli = 2.0
n_x = 2
stimulus = "X"
all_letters = ["M", "N", "Y", "A", "U", "H"]
all_letters = all_letters + (["X"] * n_x)
```
 