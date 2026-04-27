#!/usr/bin/env python
"""
Hardware Report Generator for PsychoPy Experiments

This script generates an HTML report containing:
- System information
- PsychoPy version and status
- LSL (Lab Streaming Layer) availability and test streams
- Hardware capabilities

Run this script to verify your system is ready for running PsychoPy experiments.
"""

import sys
import platform
import os
import json
import socket
import time
import numpy as np
from datetime import datetime
from pathlib import Path

# Import distance analysis module
# Add the script's directory to Python path so we can import distance_analysis
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

try:
    from distance_analysis import create_distance_plots, calculate_distances
    distance_analysis_available = True
    print(f"✓ Distance analysis module loaded successfully")
except ImportError as e:
    distance_analysis_available = False
    print(f"⚠ Distance analysis unavailable: {e}")

# Test additional packages
try:
    import psutil
    psutil_available = True
except ImportError:
    psutil_available = False

try:
    from bokeh.plotting import figure
    from bokeh.embed import components
    from bokeh.models import HoverTool
    bokeh_available = True
except ImportError:
    bokeh_available = False

# Test PsychoPy import
try:
    import psychopy
    from psychopy import __version__ as psychopy_version
    # Don't import info module here - it requires display
    psychopy_available = True
    psychopy_error = None
except Exception as e:
    psychopy_available = False
    psychopy_version = "N/A"
    psychopy_error = str(e)

# Test pylsl import and functionality
try:
    import pylsl
    pylsl_available = True
    pylsl_version = pylsl.__version__
    pylsl_error = None
except Exception as e:
    pylsl_available = False
    pylsl_version = "N/A"
    pylsl_error = str(e)


def get_system_info():
    """Collect system information including hostname."""
    try:
        hostname = socket.gethostname()
    except:
        hostname = platform.node() or "unknown-device"
    
    return {
        "hostname": hostname,
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "python_executable": sys.executable,
    }


def get_device_info():
    """Collect detailed device hardware information using psutil."""
    print("  → Collecting device information...")
    
    if not psutil_available:
        return {"status": "unavailable", "error": "psutil not installed"}
    
    try:
        # CPU information
        cpu_freq = psutil.cpu_freq()
        cpu_info = {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "frequency": {
                "current": cpu_freq.current if cpu_freq else 0,
                "max": cpu_freq.max if cpu_freq else 0,
            },
            "usage": psutil.cpu_percent(interval=1),
        }
        
        # Memory information
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk information
        disk = psutil.disk_usage('/')
        
        print("  ✓ Device information collected")
        return {
            "status": "available",
            "cpu": cpu_info,
            "memory": {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "percent": memory.percent,
            },
            "swap": {
                "total_gb": swap.total / (1024**3),
                "percent": swap.percent,
            },
            "disk": {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "percent": disk.percent,
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def test_display_info():
    """Test display and monitor information."""
    print("  → Testing display configuration...")
    
    if not psychopy_available:
        return {"status": "unavailable", "error": "PsychoPy not available"}
    
    try:
        from psychopy import monitors, visual
        import pyglet
        
        # Get all available monitors
        monitor_names = monitors.getAllMonitors()
        
        # Try to get display info without creating a window first
        display_info = {
            "available_monitors": monitor_names,
            "monitors": []
        }
        
        # Get info for each monitor
        for mon_name in monitor_names:
            mon = monitors.Monitor(mon_name)
            mon_info = {
                "name": mon_name,
                "width_cm": mon.getWidth(),
                "distance_cm": mon.getDistance(),
                "size_pix": mon.getSizePix(),
            }
            display_info["monitors"].append(mon_info)
        
        # Try to create a window to get actual display specs
        try:
            win = visual.Window(size=(800, 600), fullscr=False, allowGUI=False, 
                              monitor='testMonitor', units='pix', waitBlanking=False)
            
            display_info["actual_refresh_rate"] = f"{win.getActualFrameRate(nIdentical=10, nMaxFrames=100):.2f} Hz"
            display_info["monitor_size_pix"] = win.size
            display_info["color_space"] = win.colorSpace
            display_info["backend"] = win.winType
            
            win.close()
            print("  ✓ Display information collected (with window)")
        except Exception as win_error:
            display_info["window_error"] = str(win_error)
            display_info["headless"] = True
            print(f"  ⚠ Could not create window (headless mode): {str(win_error)[:50]}...")
        
        return {"status": "available", "details": display_info}
        
    except Exception as e:
        print(f"  ✗ Display test failed: {str(e)[:50]}...")
        return {"status": "error", "error": str(e)}


def run_psychopy_benchmark():
    """Run PsychoPy timing benchmark tests."""
    print("  → Running PsychoPy timing benchmark...")
    
    if not psychopy_available:
        return {"status": "unavailable", "error": "PsychoPy not available"}
    
    try:
        from psychopy import visual, core
        
        # Try to create a window for timing tests
        try:
            win = visual.Window(size=(800, 600), fullscr=False, allowGUI=False,
                              monitor='testMonitor', waitBlanking=True)
            
            print("    • Measuring frame timing (this takes ~10 seconds)...")
            
            # Collect frame intervals
            n_frames = 300
            frame_times = []
            
            for i in range(n_frames):
                win.flip()
                frame_times.append(core.getTime())
                
                if i % 100 == 0 and i > 0:
                    print(f"      {i}/{n_frames} frames...")
            
            # Calculate intervals
            intervals = np.diff(frame_times)
            
            # Get refresh rate
            refresh_rate = win.getActualFrameRate(nIdentical=10, nMaxFrames=100)
            expected_interval = 1.0 / refresh_rate if refresh_rate else 0.0167
            
            stats = {
                "refresh_rate_hz": f"{refresh_rate:.2f}" if refresh_rate else "N/A",
                "expected_interval_ms": f"{expected_interval * 1000:.4f}",
                "mean_interval_ms": f"{np.mean(intervals) * 1000:.4f}",
                "std_interval_ms": f"{np.std(intervals) * 1000:.4f}",
                "min_interval_ms": f"{np.min(intervals) * 1000:.4f}",
                "max_interval_ms": f"{np.max(intervals) * 1000:.4f}",
                "dropped_frames": int(np.sum(intervals > (expected_interval * 1.5))),
                "total_frames": n_frames - 1,
            }
            
            win.close()
            print("  ✓ Timing benchmark completed")
            
            return {
                "status": "available",
                "stats": stats,
                "intervals": intervals.tolist(),  # Save for plotting
            }
            
        except Exception as win_error:
            print(f"  ⚠ Benchmark skipped (no display): {str(win_error)[:50]}...")
            return {"status": "skipped", "error": "No display available", "headless": True}
            
    except Exception as e:
        print(f"  ✗ Benchmark failed: {str(e)[:50]}...")
        return {"status": "error", "error": str(e)}


def run_smoothness_test():
    """Run 90-second smoothness test with moving circle."""
    print("  → Running smoothness test (90 seconds)...")
    
    if not psychopy_available:
        return {"status": "unavailable", "error": "PsychoPy not available"}
    
    try:
        from psychopy import visual, core
        import random
        
        # Try to create a fullscreen window
        try:
            win = visual.Window(fullscr=True, allowGUI=False, monitor='testMonitor', 
                              waitBlanking=True, units='pix')
            
            # Get window size
            win_width, win_height = win.size
            
            # Create circle stimulus
            circle = visual.Circle(
                win,
                radius=10,
                fillColor='white',
                lineColor='white',
                units='pix'
            )
            
            # Initialize position and velocity
            pos_x, pos_y = 0.0, 0.0
            
            # Random direction vector, normalized
            angle = random.uniform(0, 2 * 3.14159)
            speed = 15  # pixels per frame
            vel_x = speed * np.cos(angle)
            vel_y = speed * np.sin(angle)
            
            print("    • Running 90-second smoothness test with moving circle...")
            
            # Collect frame data (times, positions, velocities)
            frame_times = []
            positions = []  # (x, y) positions
            velocities = []  # (vx, vy) velocities
            start_time = core.getTime()
            test_duration = 90  # seconds
            frame_count = 0
            
            while (core.getTime() - start_time) < test_duration:
                # Random direction change with 20% probability
                if random.random() < 0.2:
                    # Calculate current angle
                    current_angle = np.arctan2(vel_y, vel_x)
                    # Add random change within ±45 degrees (±π/4 radians)
                    angle_change = random.uniform(-np.pi/4, np.pi/4)
                    new_angle = current_angle + angle_change
                    # Update velocity with same speed, new direction
                    vel_x = speed * np.cos(new_angle)
                    vel_y = speed * np.sin(new_angle)
                
                # Update position
                pos_x += vel_x
                pos_y += vel_y
                
                # Bounce off walls
                if abs(pos_x) > (win_width / 2 - 10):
                    vel_x = -vel_x
                    pos_x = np.clip(pos_x, -(win_width / 2 - 10), (win_width / 2 - 10))
                
                if abs(pos_y) > (win_height / 2 - 10):
                    vel_y = -vel_y
                    pos_y = np.clip(pos_y, -(win_height / 2 - 10), (win_height / 2 - 10))
                
                # Set circle position
                circle.pos = (pos_x, pos_y)
                
                # Draw and flip
                circle.draw()
                win.flip()
                
                # Log data
                frame_times.append(core.getTime())
                positions.append((pos_x, pos_y))
                velocities.append((vel_x, vel_y))
                
                frame_count += 1
                
                # Progress update every 1500 frames (~30 seconds at 50Hz)
                if frame_count % 1500 == 0:
                    elapsed = core.getTime() - start_time
                    print(f"      {int(elapsed)}s / {test_duration}s ({frame_count} frames)...")
            
            # Calculate intervals
            intervals = np.diff(frame_times)
            
            # Get refresh rate
            refresh_rate = win.getActualFrameRate(nIdentical=10, nMaxFrames=100)
            expected_interval = 1.0 / refresh_rate if refresh_rate else 0.0167
            
            stats = {
                "refresh_rate_hz": f"{refresh_rate:.2f}" if refresh_rate else "N/A",
                "expected_interval_ms": f"{expected_interval * 1000:.4f}",
                "mean_interval_ms": f"{np.mean(intervals) * 1000:.4f}",
                "std_interval_ms": f"{np.std(intervals) * 1000:.4f}",
                "min_interval_ms": f"{np.min(intervals) * 1000:.4f}",
                "max_interval_ms": f"{np.max(intervals) * 1000:.4f}",
                "dropped_frames": int(np.sum(intervals > (expected_interval * 1.5))),
                "total_frames": frame_count,
                "test_duration_s": f"{test_duration}",
                "actual_duration_s": f"{frame_times[-1] - frame_times[0]:.2f}",
                "avg_speed_pxf": f"{speed:.2f}",
            }
            
            win.close()
            print("  ✓ Smoothness test completed")
            
            return {
                "status": "available",
                "stats": stats,
                "intervals": intervals.tolist(),  # Save for plotting
                "positions": positions,  # Save position data
                "velocities": velocities,  # Save velocity data
            }
            
        except Exception as win_error:
            print(f"  ⚠ Smoothness test skipped (no display): {str(win_error)[:50]}...")
            return {"status": "skipped", "error": "No display available", "headless": True}
            
    except Exception as e:
        print(f"  ✗ Smoothness test failed: {str(e)[:50]}...")
        return {"status": "error", "error": str(e)}


def generate_sampling_plot(intervals):
    """Generate interactive Bokeh plots for timing analysis."""
    print("  → Generating interactive timing plots...")
    
    if not bokeh_available:
        return None
    
    try:
        intervals_ms = np.array(intervals) * 1000  # Convert to milliseconds
        
        # Create histogram
        hist, edges = np.histogram(intervals_ms, bins=50)
        
        p_hist = figure(
            title="Frame Interval Distribution",
            x_axis_label="Interval (ms)",
            y_axis_label="Count",
            width=800,
            height=400,
        )
        
        p_hist.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
                   fill_color="navy", alpha=0.7, line_color="white")
        
        # Add mean line
        mean_interval = np.mean(intervals_ms)
        p_hist.line([mean_interval, mean_interval], [0, max(hist)],
                   line_color="red", line_width=2, legend_label=f"Mean: {mean_interval:.4f} ms")
        
        # Create time series
        p_time = figure(
            title="Frame Intervals Over Time",
            x_axis_label="Frame Number",
            y_axis_label="Interval (ms)",
            width=800,
            height=400,
        )
        
        frame_numbers = list(range(len(intervals_ms)))
        p_time.line(frame_numbers, intervals_ms, line_width=1, color="navy", alpha=0.6)
        p_time.circle(frame_numbers, intervals_ms, size=2, color="navy", alpha=0.3)
        
        # Add hover tool
        hover = HoverTool(tooltips=[("Frame", "@x{0}"), ("Interval", "@y{0.0000} ms")])
        p_time.add_tools(hover)
        
        # Generate embedded HTML
        script_hist, div_hist = components(p_hist)
        script_time, div_time = components(p_time)
        
        print("  ✓ Plots generated")
        
        return {
            "histogram": {"script": script_hist, "div": div_hist},
            "timeseries": {"script": script_time, "div": div_time},
        }
        
    except Exception as e:
        print(f"  ✗ Plot generation failed: {str(e)[:50]}...")
        return None


def test_pylsl_streams():
    """Test creating LSL outlet streams."""
    if not pylsl_available:
        return {"status": "unavailable", "error": pylsl_error, "streams": []}
    
    test_results = []
    
    # Test creating a simple marker stream
    try:
        info = pylsl.StreamInfo(
            name='TestMarkerStream',
            type='Markers',
            channel_count=1,
            nominal_srate=pylsl.IRREGULAR_RATE,
            channel_format=pylsl.cf_string,
            source_id='test_marker_001'
        )
        outlet = pylsl.StreamOutlet(info)
        test_results.append({
            "name": "TestMarkerStream",
            "type": "Markers",
            "status": "success",
            "message": "Successfully created marker outlet stream"
        })
        del outlet  # Clean up
    except Exception as e:
        test_results.append({
            "name": "TestMarkerStream",
            "type": "Markers",
            "status": "failed",
            "message": f"Failed to create marker stream: {str(e)}"
        })
    
    # Test creating a numeric data stream
    try:
        info = pylsl.StreamInfo(
            name='TestDataStream',
            type='EEG',
            channel_count=8,
            nominal_srate=250,
            channel_format=pylsl.cf_float32,
            source_id='test_data_001'
        )
        outlet = pylsl.StreamOutlet(info)
        test_results.append({
            "name": "TestDataStream",
            "type": "EEG",
            "status": "success",
            "message": "Successfully created numeric data outlet stream"
        })
        del outlet  # Clean up
    except Exception as e:
        test_results.append({
            "name": "TestDataStream",
            "type": "EEG",
            "status": "failed",
            "message": f"Failed to create data stream: {str(e)}"
        })
    
    return {
        "status": "available",
        "error": None,
        "streams": test_results
    }


def get_psychopy_info():
    """Get detailed PsychoPy information."""
    if not psychopy_available:
        return {"status": "unavailable", "error": psychopy_error, "details": {}}
    
    try:
        # Try to get runtime info (requires display)
        try:
            from psychopy import info
            runtime_info = info.RunTimeInfo(
                author=None,
                version=psychopy_version,
                win=None,
                refreshTest='grating',
                verbose=False
            )
            has_display = True
        except Exception as display_error:
            # Headless mode - no display available
            has_display = False
            runtime_info = None
        
        return {
            "status": "available",
            "error": None,
            "details": {
                "version": psychopy_version,
                "psychopy_path": os.path.dirname(psychopy.__file__),
                "headless": not has_display,
            }
        }
    except Exception as e:
        return {
            "status": "available_with_errors",
            "error": str(e),
            "details": {
                "version": psychopy_version,
                "psychopy_path": os.path.dirname(psychopy.__file__),
            }
        }


def save_report_metadata(docs_dir, system_info, timestamp, filename, psychopy_available, pylsl_available):
    """Save report metadata to JSON index."""
    reports_json = docs_dir / "reports_index.json"
    
    # Load existing reports
    if reports_json.exists():
        with open(reports_json, 'r') as f:
            reports = json.load(f)
    else:
        reports = []
    
    # Determine status
    if psychopy_available and pylsl_available:
        status = "ready"
        status_text = "✓ Ready"
    elif psychopy_available:
        status = "partial"
        status_text = "⚠ Partial"
    else:
        status = "not-ready"
        status_text = "✗ Not Ready"
    
    # Add new report
    reports.append({
        "hostname": system_info['hostname'],
        "platform": system_info['platform'],
        "architecture": system_info['architecture'],
        "timestamp": timestamp,
        "filename": filename,
        "status": status,
        "status_text": status_text,
        "psychopy_available": psychopy_available,
        "pylsl_available": pylsl_available
    })
    
    # Save updated index
    with open(reports_json, 'w') as f:
        json.dump(reports, f, indent=2)


def generate_index_html(docs_dir):
    """Generate index.html with search functionality listing all reports."""
    reports_json = docs_dir / "reports_index.json"
    
    # Load existing reports index
    if reports_json.exists():
        with open(reports_json, 'r') as f:
            reports = json.load(f)
    else:
        reports = []
    
    unique_devices = len(set(r['hostname'] for r in reports)) if reports else 0
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hardware Reports Index</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .search-box {{
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        #searchInput {{
            width: 100%;
            padding: 12px 20px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 25px;
            outline: none;
            transition: border-color 0.3s;
        }}
        #searchInput:focus {{
            border-color: #667eea;
        }}
        .reports-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .report-card {{
            background: white;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }}
        .report-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        .device-name {{
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .timestamp {{
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .platform {{
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 12px;
            margin: 5px 5px 5px 0;
        }}
        .status-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 12px;
            margin: 5px 5px 5px 0;
        }}
        .status-ready {{
            background: #2ecc71;
            color: white;
        }}
        .status-partial {{
            background: #f39c12;
            color: white;
        }}
        .status-not-ready {{
            background: #e74c3c;
            color: white;
        }}
        .no-results {{
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
            font-size: 18px;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        .stat-card {{
            flex: 1;
            min-width: 150px;
            background: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .stat-label {{
            color: #7f8c8d;
            font-size: 14px;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 Hardware Reports Index</h1>
        <p style="color: #7f8c8d; margin-bottom: 20px;">PsychoPy Environment Testing Reports</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="totalReports">{len(reports)}</div>
                <div class="stat-label">Total Reports</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="uniqueDevices">{unique_devices}</div>
                <div class="stat-label">Unique Devices</div>
            </div>
        </div>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="🔍 Search by device name, platform, or date..." onkeyup="filterReports()">
        </div>
        
        <div class="reports-grid" id="reportsGrid">
            {''.join(f'''
            <div class="report-card" onclick="window.location.href='{report['filename']}'" 
                 data-hostname="{report['hostname']}" 
                 data-platform="{report['platform']}" 
                 data-timestamp="{report['timestamp']}">
                <div class="device-name">{report['hostname']}</div>
                <div class="timestamp">{report['timestamp']}</div>
                <div>
                    <span class="platform">{report['platform']} {report['architecture']}</span>
                    <span class="status-badge status-{report['status']}">{report['status_text']}</span>
                </div>
            </div>
            ''' for report in sorted(reports, key=lambda x: x['timestamp'], reverse=True)) if reports else '<div class="no-results">No reports yet. Generate your first report!</div>'}
        </div>
        
        <div id="noResults" class="no-results" style="display: none;">
            No reports found matching your search.
        </div>
    </div>
    
    <script>
        function filterReports() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.report-card');
            let visibleCount = 0;
            
            cards.forEach(card => {{
                const hostname = (card.dataset.hostname || '').toLowerCase();
                const platform = (card.dataset.platform || '').toLowerCase();
                const timestamp = (card.dataset.timestamp || '').toLowerCase();
                const matches = hostname.includes(searchTerm) || 
                               platform.includes(searchTerm) || 
                               timestamp.includes(searchTerm);
                
                card.style.display = matches ? 'block' : 'none';
                if (matches) visibleCount++;
            }});
            
            document.getElementById('noResults').style.display = visibleCount === 0 ? 'block' : 'none';
            document.getElementById('reportsGrid').style.display = visibleCount === 0 ? 'none' : 'grid';
        }}
    </script>
</body>
</html>
"""
    
    index_path = docs_dir / "index.html"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return index_path


def generate_html_report(output_path):
    """Generate HTML hardware report with device name and timestamp."""
    
    print("\n" + "="*60)
    print("Starting Hardware Report Generation")
    print("="*60 + "\n")
    
    system_info = get_system_info()
    hostname = system_info['hostname']
    
    # Run all tests with progress indicators
    device_info = get_device_info()
    display_info = test_display_info()
    benchmark_results = run_psychopy_benchmark()
    smoothness_results = run_smoothness_test()
    psychopy_info_data = get_psychopy_info()
    lsl_test_results = test_pylsl_streams()
    
    # Generate plots if benchmark data available
    plots = None
    if benchmark_results.get("status") == "available" and benchmark_results.get("intervals"):
        plots = generate_sampling_plot(benchmark_results["intervals"])
    
    # Generate plots for smoothness test
    smoothness_plots = None
    if smoothness_results.get("status") == "available" and smoothness_results.get("intervals"):
        smoothness_plots = generate_sampling_plot(smoothness_results["intervals"])
    
    # Generate distance analysis plots
    distance_analysis = None
    if (distance_analysis_available and smoothness_results.get("status") == "available" 
        and smoothness_results.get("positions")):
        print("  → Generating distance analysis plots...")
        frame_times = [0] + list(np.cumsum(smoothness_results["intervals"]))
        distances = calculate_distances(smoothness_results["positions"])
        distance_analysis = create_distance_plots(frame_times, distances, 
                                                  smoothness_results["positions"])
        print("  ✓ Distance analysis completed")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hardware Report - {hostname}</title>
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-3.8.2.min.js" crossorigin="anonymous"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 5px;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #3498db;
            text-decoration: none;
            font-weight: bold;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
        .section {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .status {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .status.success {{
            background-color: #2ecc71;
            color: white;
        }}
        .status.failed {{
            background-color: #e74c3c;
            color: white;
        }}
        .status.unavailable {{
            background-color: #95a5a6;
            color: white;
        }}
        .status.warning {{
            background-color: #f39c12;
            color: white;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .error-box {{
            background-color: #ffe6e6;
            border-left: 4px solid #e74c3c;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .timestamp {{
            color: #7f8c8d;
            font-style: italic;
            margin-bottom: 20px;
        }}
        code {{
            background-color: #ecf0f1;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        .tabs {{
            display: flex;
            border-bottom: 2px solid #3498db;
            margin: 20px 0;
        }}
        .tab {{
            padding: 12px 24px;
            cursor: pointer;
            background-color: #ecf0f1;
            border: none;
            outline: none;
            transition: 0.3s;
            font-size: 16px;
            font-weight: 500;
            margin-right: 2px;
            border-radius: 4px 4px 0 0;
        }}
        .tab:hover {{
            background-color: #bdc3c7;
        }}
        .tab.active {{
            background-color: #3498db;
            color: white;
        }}
        .tab-content {{
            display: none;
            animation: fadeIn 0.5s;
        }}
        .tab-content.active {{
            display: block;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
    </style>
</head>
<body>
    <a href="index.html" class="back-link">← Back to Index</a>
    <h1>🔧 Hardware Report - {hostname}</h1>
    <p class="timestamp">Generated: {timestamp}</p>
    
    <div class="tabs">
        <button class="tab active" onclick="openTab(event, 'hardware-tab')">Hardware Tests</button>
        <button class="tab" onclick="openTab(event, 'smoothness-tab')">Smoothness Test</button>
        <button class="tab" onclick="openTab(event, 'distance-tab')">Distance Analysis</button>
    </div>
    
    <div id="hardware-tab" class="tab-content active">
    
    <div class="section">
        <h2>System Information</h2>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Hostname</td><td><strong>{system_info['hostname']}</strong></td></tr>
            <tr><td>Platform</td><td>{system_info['platform']}</td></tr>
            <tr><td>Platform Release</td><td>{system_info['platform_release']}</td></tr>
            <tr><td>Architecture</td><td>{system_info['architecture']}</td></tr>
            <tr><td>Processor</td><td>{system_info['processor']}</td></tr>
            <tr><td>Python Version</td><td>{system_info['python_version']}</td></tr>
            <tr><td>Python Executable</td><td><code>{system_info['python_executable']}</code></td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>PsychoPy Status</h2>
        <span class="status {'success' if psychopy_available else 'failed'}">
            {'✓ Available' if psychopy_available else '✗ Unavailable'}
        </span>
        {'<p><strong>Version:</strong> ' + str(psychopy_info_data['details'].get('version', 'N/A')) + '</p>' if psychopy_available else ''}
        {'<p><strong>Path:</strong> <code>' + str(psychopy_info_data['details'].get('psychopy_path', 'N/A')) + '</code></p>' if psychopy_available else ''}
        {f'<div class="error-box"><strong>Error:</strong> {psychopy_error}</div>' if psychopy_error else ''}
    </div>
    
    <div class="section">
        <h2>Lab Streaming Layer (LSL) Status</h2>
        <span class="status {'success' if pylsl_available else 'failed'}">
            {'✓ Available' if pylsl_available else '✗ Unavailable'}
        </span>
        {'<p><strong>Version:</strong> ' + str(pylsl_version) + '</p>' if pylsl_available else ''}
        {f'<div class="error-box"><strong>Error:</strong> {pylsl_error}</div>' if pylsl_error else ''}
        
        {f'''
        <h3>LSL Stream Tests</h3>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            {''.join(f"<tr><td>{stream['name']}</td><td>{stream['type']}</td><td><span class='status {stream['status']}'>{stream['status']}</span></td><td>{stream['message']}</td></tr>" for stream in lsl_test_results['streams'])}
        </table>
        ''' if pylsl_available and lsl_test_results['streams'] else ''}
    </div>
    
    <div class="section">
        <h2>Device Hardware</h2>
        {f'''
        <h3>CPU</h3>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Physical Cores</td><td>{device_info['cpu']['physical_cores']}</td></tr>
            <tr><td>Logical Cores</td><td>{device_info['cpu']['logical_cores']}</td></tr>
            <tr><td>Current Frequency</td><td>{device_info['cpu']['frequency']['current']:.2f} MHz</td></tr>
            <tr><td>Max Frequency</td><td>{device_info['cpu']['frequency']['max']:.2f} MHz</td></tr>
            <tr><td>CPU Usage</td><td>{device_info['cpu']['usage']:.1f}%</td></tr>
        </table>
        
        <h3>Memory</h3>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Total RAM</td><td>{device_info['memory']['total_gb']:.2f} GB</td></tr>
            <tr><td>Available RAM</td><td>{device_info['memory']['available_gb']:.2f} GB</td></tr>
            <tr><td>RAM Usage</td><td>{device_info['memory']['percent']:.1f}%</td></tr>
            <tr><td>Total Swap</td><td>{device_info['swap']['total_gb']:.2f} GB</td></tr>
            <tr><td>Swap Usage</td><td>{device_info['swap']['percent']:.1f}%</td></tr>
        </table>
        
        <h3>Disk</h3>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Total Disk</td><td>{device_info['disk']['total_gb']:.2f} GB</td></tr>
            <tr><td>Used Disk</td><td>{device_info['disk']['used_gb']:.2f} GB</td></tr>
            <tr><td>Disk Usage</td><td>{device_info['disk']['percent']:.1f}%</td></tr>
        </table>
        ''' if device_info['status'] == 'available' else f'<div class="error-box">Device information unavailable: {device_info.get("error", "Unknown error")}</div>'}
    </div>
    
    <div class="section">
        <h2>Display Information</h2>
        <span class="status {('success' if display_info['status'] == 'available' else 'failed')}">
            {'✓ Display Test Completed' if display_info['status'] == 'available' else '✗ Display Test Failed'}
        </span>
        {f'''
        <h3>Monitor Configuration</h3>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Available Monitors</td><td>{', '.join(display_info['details'].get('available_monitors', []))}</td></tr>
            <tr><td>Monitor Count</td><td>{len(display_info['details'].get('monitors', []))}</td></tr>
        </table>
        
        {('<h3>Display Specifications</h3><table><tr><th>Property</th><th>Value</th></tr>' +
          ('<tr><td>Actual Refresh Rate</td><td>' + str(display_info['details'].get('actual_refresh_rate', 'N/A')) + '</td></tr>' if 'actual_refresh_rate' in display_info['details'] else '') +
          ('<tr><td>Resolution</td><td>' + str(display_info['details'].get('monitor_size_pix', 'N/A')) + '</td></tr>' if 'monitor_size_pix' in display_info['details'] else '') +
          ('<tr><td>Color Space</td><td>' + str(display_info['details'].get('color_space', 'N/A')) + '</td></tr>' if 'color_space' in display_info['details'] else '') +
          ('<tr><td>Backend</td><td>' + str(display_info['details'].get('backend', 'N/A')) + '</td></tr>' if 'backend' in display_info['details'] else '') +
          '</table>') if not display_info['details'].get('headless') else ''}
        
        {('<p><strong>Note:</strong> Running in headless mode - ' + str(display_info['details'].get('window_error', '')) + '</p>') if display_info['details'].get('headless') else ''}
        ''' if display_info['status'] == 'available' else f'<div class="error-box">Display test failed: {display_info.get("error", "Unknown error")}</div>'}
    </div>
    
    <div class="section">
        <h2>PsychoPy Timing Benchmark</h2>
        <span class="status {('success' if benchmark_results['status'] == 'available' else 'failed')}">
            {'✓ Benchmark Completed' if benchmark_results['status'] == 'available' else '✗ Benchmark Failed'}
        </span>
        {f'''
        <p>Collected {benchmark_results['stats']['total_frames']} frame intervals</p>
        
        <h3>Frame Timing Statistics</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Refresh Rate</td><td>{benchmark_results['stats']['refresh_rate_hz']} Hz</td></tr>
            <tr><td>Expected Interval</td><td>{benchmark_results['stats']['expected_interval_ms']} ms</td></tr>
            <tr><td>Mean Interval</td><td>{benchmark_results['stats']['mean_interval_ms']} ms</td></tr>
            <tr><td>Std Dev</td><td>{benchmark_results['stats']['std_interval_ms']} ms</td></tr>
            <tr><td>Min Interval</td><td>{benchmark_results['stats']['min_interval_ms']} ms</td></tr>
            <tr><td>Max Interval</td><td>{benchmark_results['stats']['max_interval_ms']} ms</td></tr>
            <tr><td>Dropped Frames</td><td>{benchmark_results['stats']['dropped_frames']}</td></tr>
        </table>
        ''' if benchmark_results['status'] == 'available' else f'<div class="error-box">Benchmark unavailable: {benchmark_results.get("error", "Unknown error")}</div>'}
    </div>
    
    {f'''
    <div class="section">
        <h2>Sampling Distribution Analysis</h2>
        <p>Interactive visualization of frame interval timing distribution and time-series.</p>
        {plots['histogram']['script']}
        {plots['timeseries']['script']}
        <div style="display: flex; flex-direction: column; gap: 20px; margin-top: 20px;">
            <div>
                <h3>Frame Interval Distribution</h3>
                {plots['histogram']['div']}
            </div>
            <div>
                <h3>Frame Intervals Over Time</h3>
                {plots['timeseries']['div']}
            </div>
        </div>
    </div>
    ''' if plots else ''}
    
    <div class="section">
        <h2>Summary</h2>
        <ul>
            <li><strong>PsychoPy:</strong> {'✓ Ready' if psychopy_available else '✗ Not available - needs installation'}</li>
            <li><strong>LSL:</strong> {'✓ Ready' if pylsl_available else '✗ Not available - needs installation'}</li>
            <li><strong>Overall Status:</strong> 
                <span class="status {'success' if (psychopy_available and pylsl_available) else 'warning' if psychopy_available else 'failed'}">
                    {'✓ System Ready' if (psychopy_available and pylsl_available) else '⚠ Partially Ready' if psychopy_available else '✗ Not Ready'}
                </span>
            </li>
        </ul>
    </div>
    
    </div><!-- End Hardware Tab -->
    
    <div id="smoothness-tab" class="tab-content">
    
    <div class="section">
        <h2>Smoothness Test Results</h2>
        <p>90-second test with a moving white circle (10px radius, 15px/frame speed) in fullscreen mode.</p>
        <span class="status {('success' if smoothness_results['status'] == 'available' else 'failed')}">
            {'✓ Smoothness Test Completed' if smoothness_results['status'] == 'available' else '✗ Smoothness Test Failed'}
        </span>
        {f'''
        <h3>Test Configuration</h3>
        <table>
            <tr><th>Parameter</th><th>Value</th></tr>
            <tr><td>Test Duration</td><td>{smoothness_results['stats']['test_duration_s']} seconds (target)</td></tr>
            <tr><td>Actual Duration</td><td>{smoothness_results['stats']['actual_duration_s']} seconds</td></tr>
            <tr><td>Total Frames</td><td>{smoothness_results['stats']['total_frames']}</td></tr>
            <tr><td>Circle Radius</td><td>10 pixels</td></tr>
            <tr><td>Movement Speed</td><td>15 pixels/frame</td></tr>
        </table>
        
        <h3>Frame Timing Statistics</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Refresh Rate</td><td>{smoothness_results['stats']['refresh_rate_hz']} Hz</td></tr>
            <tr><td>Expected Interval</td><td>{smoothness_results['stats']['expected_interval_ms']} ms</td></tr>
            <tr><td>Mean Interval</td><td>{smoothness_results['stats']['mean_interval_ms']} ms</td></tr>
            <tr><td>Std Dev</td><td>{smoothness_results['stats']['std_interval_ms']} ms</td></tr>
            <tr><td>Min Interval</td><td>{smoothness_results['stats']['min_interval_ms']} ms</td></tr>
            <tr><td>Max Interval</td><td>{smoothness_results['stats']['max_interval_ms']} ms</td></tr>
            <tr><td>Dropped Frames</td><td>{smoothness_results['stats']['dropped_frames']}</td></tr>
        </table>
        ''' if smoothness_results['status'] == 'available' else f'<div class="error-box">Smoothness test unavailable: {smoothness_results.get("error", "Unknown error")}</div>'}
    </div>
    
    {f'''
    <div class="section">
        <h2>Smoothness Test - Sampling Distribution Analysis</h2>
        <p>Interactive visualization of frame interval timing distribution and time-series for the 90-second smoothness test.</p>
        {smoothness_plots['histogram']['script']}
        {smoothness_plots['timeseries']['script']}
        <div style="display: flex; flex-direction: column; gap: 20px; margin-top: 20px;">
            <div>
                <h3>Frame Interval Distribution</h3>
                {smoothness_plots['histogram']['div']}
            </div>
            <div>
                <h3>Frame Intervals Over Time</h3>
                {smoothness_plots['timeseries']['div']}
            </div>
        </div>
    </div>
    ''' if smoothness_plots else ''}
    
    </div><!-- End Smoothness Tab -->
    
    <div id="distance-tab" class="tab-content">
    
    {f'''
    <div class="section">
        <h2>Distance Analysis</h2>
        <p>Analysis of the circle's distance from screen center during the 90-second smoothness test.</p>
        
        <h3>Sampling Statistics</h3>
        <table>
            <tr><th>Metric</th><th>Original Signal</th><th>Interpolated Signal</th></tr>
            <tr>
                <td>Sampling Rate</td>
                <td>{distance_analysis['statistics']['sampling_rates']['original_avg_hz']:.2f} Hz (avg)</td>
                <td>{distance_analysis['statistics']['sampling_rates']['interpolated_hz']:.2f} Hz (constant)</td>
            </tr>
            <tr>
                <td>Mean Distance</td>
                <td>{distance_analysis['statistics']['original']['mean']:.2f} px</td>
                <td>{distance_analysis['statistics']['interpolated']['mean']:.2f} px</td>
            </tr>
            <tr>
                <td>Std Dev</td>
                <td>{distance_analysis['statistics']['original']['std']:.2f} px</td>
                <td>{distance_analysis['statistics']['interpolated']['std']:.2f} px</td>
            </tr>
            <tr>
                <td>Min Distance</td>
                <td>{distance_analysis['statistics']['original']['min']:.2f} px</td>
                <td>{distance_analysis['statistics']['interpolated']['min']:.2f} px</td>
            </tr>
            <tr>
                <td>Max Distance</td>
                <td>{distance_analysis['statistics']['original']['max']:.2f} px</td>
                <td>{distance_analysis['statistics']['interpolated']['max']:.2f} px</td>
            </tr>
            <tr>
                <td>Median</td>
                <td>{distance_analysis['statistics']['original']['median']:.2f} px</td>
                <td>{distance_analysis['statistics']['interpolated']['median']:.2f} px</td>
            </tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Trajectory Visualization</h2>
        <p>2D trajectory of the circle with color-coded distance from center.</p>
        {distance_analysis['plots']['trajectory']['script']}
        {distance_analysis['plots']['trajectory']['div']}
    </div>
    
    <div class="section">
        <h2>Distance Distribution</h2>
        <p>Histogram showing the distribution of distances from the center of the screen.</p>
        {distance_analysis['plots']['distribution']['script']}
        {distance_analysis['plots']['distribution']['div']}
    </div>
    
    <div class="section">
        <h2>Distance Signal - Original Sampling</h2>
        <p>Distance from center at the original variable sampling rate.</p>
        {distance_analysis['plots']['original']['script']}
        {distance_analysis['plots']['original']['div']}
    </div>
    
    <div class="section">
        <h2>Distance Signal - Interpolated to Constant Rate</h2>
        <p>Distance signal interpolated to constant 60 Hz sampling rate using cubic splines.</p>
        {distance_analysis['plots']['interpolated']['script']}
        {distance_analysis['plots']['interpolated']['div']}
    </div>
    
    <div class="section">
        <h2>Spectral Analysis</h2>
        <p>Power spectral density comparison between original and interpolated signals.</p>
        {distance_analysis['plots']['spectrum']['script']}
        {distance_analysis['plots']['spectrum']['div']}
    </div>
    
    <div class="section">
        <h2>Random Window Analysis</h2>
        <p>Analysis of 60 random 2-second windows from the interpolated signal and their average.</p>
        {distance_analysis['plots']['windows']['script']}
        {distance_analysis['plots']['windows']['div']}
    </div>
    ''' if distance_analysis else '<div class="section"><p>Distance analysis unavailable (requires successful smoothness test)</p></div>'}
    
    </div><!-- End Distance Tab -->
    
    <script>
    function openTab(evt, tabName) {{
        var i, tabcontent, tablinks;
        tabcontent = document.getElementsByClassName("tab-content");
        for (i = 0; i < tabcontent.length; i++) {{
            tabcontent[i].style.display = "none";
            tabcontent[i].classList.remove("active");
        }}
        tablinks = document.getElementsByClassName("tab");
        for (i = 0; i < tablinks.length; i++) {{
            tablinks[i].classList.remove("active");
        }}
        document.getElementById(tabName).style.display = "block";
        document.getElementById(tabName).classList.add("active");
        evt.currentTarget.classList.add("active");
    }}
    </script>
</body>
</html>
"""
    
    # Write the HTML report
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n{'='*60}")
    print(f"Hardware report generated successfully!")
    print(f"Location: {output_path}")
    print(f"{'='*60}\n")
    
    # Print summary to console
    print("Summary:")
    print(f"  PsychoPy: {'✓ Available (v' + psychopy_version + ')' if psychopy_available else '✗ Unavailable'}")
    print(f"  pylsl:    {'✓ Available (v' + pylsl_version + ')' if pylsl_available else '✗ Unavailable'}")
    
    if lsl_test_results['streams']:
        print(f"\n  LSL Stream Tests:")
        for stream in lsl_test_results['streams']:
            status_symbol = '✓' if stream['status'] == 'success' else '✗'
            print(f"    {status_symbol} {stream['name']} ({stream['type']}): {stream['status']}")
    
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    # Output dir resolution:
    #   1. $PSYCHOPY_REPORT_DIR if set (explicit override)
    #   2. $PWD/docs if invoked from a writable project root
    #   3. $XDG_DATA_HOME/psychopy-flake/reports/ as a per-user fallback
    # When invoked via `nix run`, the script lives in /nix/store (read-only),
    # so the legacy `script_dir.parent / "docs"` is never appropriate.
    env_override = os.environ.get("PSYCHOPY_REPORT_DIR")
    if env_override:
        docs_dir = Path(env_override)
    else:
        cwd_docs = Path.cwd() / "docs"
        try:
            cwd_docs.mkdir(exist_ok=True)
            docs_dir = cwd_docs
        except (OSError, PermissionError):
            xdg = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
            docs_dir = Path(xdg) / "psychopy-flake" / "reports"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Get system info and generate timestamped filename
    system_info = get_system_info()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    hostname = system_info['hostname']
    filename = f"hardware_{hostname}_{timestamp}.html"
    
    # Generate individual report
    output_file = docs_dir / filename
    generate_html_report(output_file)
    
    # Save metadata and generate index
    save_report_metadata(docs_dir, system_info, timestamp, filename, psychopy_available, pylsl_available)
    index_path = generate_index_html(docs_dir)
    
    print(f"\n{'='*60}")
    print(f"Hardware report generated successfully!")
    print(f"Device: {hostname}")
    print(f"Report: {output_file}")
    print(f"Index: {index_path}")
    print(f"{'='*60}\n")
    
    # Print summary to console
    print("Summary:")
    print(f"  PsychoPy: {'✓ Available (v' + psychopy_version + ')' if psychopy_available else '✗ Unavailable'}")
    print(f"  pylsl:    {'✓ Available (v' + pylsl_version + ')' if pylsl_available else '✗ Unavailable'}")
    
    lsl_test_results = test_pylsl_streams()
    if lsl_test_results['streams']:
        print(f"\n  LSL Stream Tests:")
        for stream in lsl_test_results['streams']:
            status_symbol = '✓' if stream['status'] == 'success' else '✗'
            print(f"    {status_symbol} {stream['name']} ({stream['type']}): {stream['status']}")
    
    print(f"\n{'='*60}\n")
