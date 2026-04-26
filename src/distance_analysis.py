#!/usr/bin/env python3
"""
Distance Analysis Module
Analyzes distance from moving target to screen center with spectral analysis.
"""

import numpy as np
from scipy import interpolate, signal
from bokeh.plotting import figure
from bokeh.layouts import column
from bokeh.models import HoverTool
from bokeh.embed import components


def calculate_distances(positions):
    """Calculate Euclidean distance from each position to center (0,0)."""
    distances = [np.sqrt(x**2 + y**2) for x, y in positions]
    return np.array(distances)


def interpolate_signal(times, signal_data, target_rate_hz=60):
    """
    Interpolate signal to constant sampling rate.
    
    Args:
        times: Array of timestamps
        signal_data: Array of signal values
        target_rate_hz: Target sampling rate in Hz
        
    Returns:
        uniform_times, interpolated_signal
    """
    # Create uniform time grid
    duration = times[-1] - times[0]
    n_samples = int(duration * target_rate_hz)
    uniform_times = np.linspace(times[0], times[-1], n_samples)
    
    # Cubic spline interpolation
    interp_func = interpolate.interp1d(times, signal_data, kind='cubic', 
                                       bounds_error=False, fill_value='extrapolate')
    interpolated_signal = interp_func(uniform_times)
    
    return uniform_times, interpolated_signal


def compute_spectrum(signal_data, sampling_rate):
    """
    Compute power spectral density using Welch's method.
    
    Args:
        signal_data: Signal array
        sampling_rate: Sampling rate in Hz
        
    Returns:
        frequencies, power
    """
    frequencies, power = signal.welch(signal_data, fs=sampling_rate, 
                                     nperseg=min(256, len(signal_data)//4))
    return frequencies, power


def get_signal_statistics(signal_data, name="Signal"):
    """Calculate comprehensive statistics for a signal."""
    return {
        "name": name,
        "mean": float(np.mean(signal_data)),
        "std": float(np.std(signal_data)),
        "min": float(np.min(signal_data)),
        "max": float(np.max(signal_data)),
        "median": float(np.median(signal_data)),
        "q25": float(np.percentile(signal_data, 25)),
        "q75": float(np.percentile(signal_data, 75)),
    }


def extract_random_windows(signal_data, window_size, n_windows=60, seed=42):
    """
    Extract random windows from signal and compute average.
    
    Args:
        signal_data: Signal array
        window_size: Size of each window in samples
        n_windows: Number of windows to extract
        seed: Random seed for reproducibility
        
    Returns:
        windows, average_window, window_starts
    """
    np.random.seed(seed)
    
    max_start = len(signal_data) - window_size
    if max_start <= 0:
        return None, None, None
    
    # Random window start positions
    window_starts = np.random.choice(max_start, size=n_windows, replace=False)
    window_starts = np.sort(window_starts)
    
    # Extract windows
    windows = []
    for start in window_starts:
        windows.append(signal_data[start:start + window_size])
    
    windows = np.array(windows)
    average_window = np.mean(windows, axis=0)
    
    return windows, average_window, window_starts


def create_distance_plots(frame_times, distances, positions):
    """
    Create comprehensive Bokeh plots for distance analysis.
    
    Returns:
        Dictionary with embedded HTML components
    """
    # Normalize times to start at 0
    times = np.array(frame_times) - frame_times[0]
    
    # 1. Original distance signal
    p_original = figure(
        title="Distance to Center (Original Sampling)",
        x_axis_label="Time (s)",
        y_axis_label="Distance (pixels)",
        width=900,
        height=300,
    )
    p_original.line(times, distances, line_width=1, color="navy", alpha=0.7)
    hover = HoverTool(tooltips=[("Time", "@x{0.00}s"), ("Distance", "@y{0.0} px")])
    p_original.add_tools(hover)
    
    # 2. Interpolated signal
    target_rate = 60  # Hz
    uniform_times, interp_distances = interpolate_signal(times, distances, target_rate)
    
    p_interp = figure(
        title=f"Distance to Center (Interpolated to {target_rate} Hz)",
        x_axis_label="Time (s)",
        y_axis_label="Distance (pixels)",
        width=900,
        height=300,
    )
    p_interp.line(uniform_times, interp_distances, line_width=1, color="darkgreen", alpha=0.7)
    hover_interp = HoverTool(tooltips=[("Time", "@x{0.00}s"), ("Distance", "@y{0.0} px")])
    p_interp.add_tools(hover_interp)
    
    # 3. Spectral analysis
    # Original signal spectrum
    sampling_intervals = np.diff(times)
    avg_sampling_rate = 1.0 / np.mean(sampling_intervals)
    freqs_orig, power_orig = compute_spectrum(distances, avg_sampling_rate)
    
    # Interpolated signal spectrum
    freqs_interp, power_interp = compute_spectrum(interp_distances, target_rate)
    
    p_spectrum = figure(
        title="Power Spectral Density Comparison",
        x_axis_label="Frequency (Hz)",
        y_axis_label="Power (dB)",
        width=900,
        height=350,
        y_axis_type="log",
    )
    p_spectrum.line(freqs_orig, power_orig, line_width=2, color="navy", 
                   alpha=0.7, legend_label="Original")
    p_spectrum.line(freqs_interp, power_interp, line_width=2, color="darkgreen", 
                   alpha=0.7, legend_label="Interpolated")
    p_spectrum.legend.location = "top_right"
    
    # 4. Random windows analysis
    window_duration = 2.0  # seconds
    window_size = int(target_rate * window_duration)
    n_windows = 60
    
    windows, avg_window, window_starts = extract_random_windows(
        interp_distances, window_size, n_windows
    )
    
    p_windows = figure(
        title=f"Random {window_duration}s Windows (n={n_windows})",
        x_axis_label="Time within window (s)",
        y_axis_label="Distance (pixels)",
        width=900,
        height=300,
    )
    
    if windows is not None:
        window_time = np.linspace(0, window_duration, window_size)
        
        # Plot individual windows with transparency
        for i, window in enumerate(windows):
            if i == 0:
                p_windows.line(window_time, window, line_width=1, color="gray", 
                             alpha=0.3, legend_label="Individual windows")
            else:
                p_windows.line(window_time, window, line_width=1, color="gray", alpha=0.3)
        
        # Plot average window
        p_windows.line(window_time, avg_window, line_width=3, color="red", 
                      alpha=0.9, legend_label="Average")
        p_windows.legend.location = "top_right"
    
    # 5. Trajectory visualization (XY plot)
    x_coords = [p[0] for p in positions]
    y_coords = [p[1] for p in positions]
    
    p_trajectory = figure(
        title="Circle Trajectory",
        x_axis_label="X Position (pixels)",
        y_axis_label="Y Position (pixels)",
        width=600,
        height=600,
        match_aspect=True,
    )
    
    # Color map based on distance
    from bokeh.models import LinearColorMapper, ColumnDataSource
    from bokeh.palettes import Viridis256
    
    color_mapper = LinearColorMapper(palette=Viridis256, low=min(distances), high=max(distances))
    
    # Create a data source with all coordinates and distances
    trajectory_source = ColumnDataSource(data={
        'x': x_coords,
        'y': y_coords,
        'distance': distances
    })
    
    p_trajectory.scatter('x', 'y', size=2, alpha=0.3,
                        color={'field': 'distance', 'transform': color_mapper},
                        source=trajectory_source)
    
    # Add center marker
    p_trajectory.circle([0], [0], size=10, color="red", alpha=0.8, legend_label="Center")
    p_trajectory.legend.location = "top_right"
    
    # 6. Distance distribution histogram
    hist, edges = np.histogram(distances, bins=50)
    p_distribution = figure(
        title="Distance Distribution",
        x_axis_label="Distance from Center (pixels)",
        y_axis_label="Frequency",
        width=800,
        height=400,
    )
    p_distribution.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
                       fill_color="steelblue", line_color="white", alpha=0.7)
    
    # Add vertical lines for mean and median
    mean_dist = np.mean(distances)
    median_dist = np.median(distances)
    
    from bokeh.models import Span
    mean_line = Span(location=mean_dist, dimension='height', line_color='red', 
                     line_width=2, line_dash='dashed')
    median_line = Span(location=median_dist, dimension='height', line_color='green', 
                       line_width=2, line_dash='dashed')
    p_distribution.add_layout(mean_line)
    p_distribution.add_layout(median_line)
    
    # Add legend manually with text annotations
    from bokeh.models import Label
    p_distribution.add_layout(Label(x=mean_dist, y=max(hist)*0.95, 
                                   text=f'Mean: {mean_dist:.1f}px', 
                                   text_color='red', text_font_size='10pt'))
    p_distribution.add_layout(Label(x=median_dist, y=max(hist)*0.85, 
                                   text=f'Median: {median_dist:.1f}px', 
                                   text_color='green', text_font_size='10pt'))
    
    # Generate embedded HTML
    script1, div1 = components(p_original)
    script2, div2 = components(p_interp)
    script3, div3 = components(p_spectrum)
    script4, div4 = components(p_windows)
    script5, div5 = components(p_trajectory)
    script6, div6 = components(p_distribution)
    
    # Calculate statistics
    stats_original = get_signal_statistics(distances, "Original Signal")
    stats_interp = get_signal_statistics(interp_distances, "Interpolated Signal")
    
    return {
        "plots": {
            "original": {"script": script1, "div": div1},
            "interpolated": {"script": script2, "div": div2},
            "spectrum": {"script": script3, "div": div3},
            "windows": {"script": script4, "div": div4},
            "trajectory": {"script": script5, "div": div5},
            "distribution": {"script": script6, "div": div6},
        },
        "statistics": {
            "original": stats_original,
            "interpolated": stats_interp,
            "sampling_rates": {
                "original_avg_hz": float(avg_sampling_rate),
                "original_std_hz": float(1.0 / np.std(sampling_intervals)),
                "interpolated_hz": float(target_rate),
            }
        }
    }
