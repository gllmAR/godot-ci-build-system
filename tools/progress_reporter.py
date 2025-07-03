#!/usr/bin/env python3
"""
Progress Reporter for SCons Build System
========================================

Provides real-time build progress tracking and reporting with visual feedback.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class BuildStats:
    """Track build statistics"""
    total_targets: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    target_times: Dict[str, float] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.completed == 0:
            return 0.0
        return (self.completed - self.failed) / self.completed * 100
    
    @property
    def elapsed_time(self) -> timedelta:
        """Get elapsed time"""
        if not self.start_time:
            return timedelta(0)
        end = self.end_time or datetime.now()
        return end - self.start_time
    
    @property
    def estimated_remaining(self) -> Optional[timedelta]:
        """Estimate remaining time based on current progress"""
        if self.completed == 0 or self.total_targets == 0:
            return None
        
        avg_time_per_target = self.elapsed_time.total_seconds() / self.completed
        remaining_targets = self.total_targets - self.completed
        return timedelta(seconds=avg_time_per_target * remaining_targets)


class ProgressReporter:
    """Real-time build progress reporter with visual feedback"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.stats = BuildStats()
        self._lock = threading.Lock()
        self._update_thread: Optional[threading.Thread] = None
        self._stop_updates = threading.Event()
        self._last_was_progress = False
        
    def start_build(self, total_targets: int):
        """Start tracking build progress"""
        with self._lock:
            self.stats = BuildStats(
                total_targets=total_targets,
                start_time=datetime.now()
            )
        
        print(f"🚀 Starting build of {total_targets} targets")
        print("=" * 60)
        
        # Start progress update thread
        self._stop_updates.clear()
        self._update_thread = threading.Thread(target=self._progress_updater, daemon=True)
        self._update_thread.start()
    
    def target_started(self, target_name: str):
        """Report that a target has started building"""
        if self.verbose:
            print(f"🔄 Building: {target_name}")
    
    def target_completed(self, target_name: str, success: bool, duration: float, 
                        output_size: Optional[int] = None):
        """Report that a target has completed"""
        with self._lock:
            self.stats.completed += 1
            if not success:
                self.stats.failed += 1
            self.stats.target_times[target_name] = duration
        
        # Immediate feedback for completed targets
        status = "✅" if success else "❌"
        size_info = f" ({self._format_size(output_size)})" if output_size else ""
        duration_str = f"{duration:.2f}s"
        
        print(f"{status} {target_name} - {duration_str}{size_info}")
        
        if not success and self.verbose:
            print(f"   ⚠️  Build failed for {target_name}")
    
    def target_skipped(self, target_name: str, reason: str):
        """Report that a target was skipped"""
        with self._lock:
            self.stats.skipped += 1
        
        if self.verbose:
            print(f"⏭️  Skipped: {target_name} - {reason}")
    
    def finish_build(self):
        """Finish tracking and show final summary"""
        # Stop progress updates
        self._stop_updates.set()
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=1.0)
        
        with self._lock:
            self.stats.end_time = datetime.now()
        
        self._print_final_summary()
    
    def _progress_updater(self):
        """Background thread for progress updates"""
        while not self._stop_updates.wait(10.0):  # Update every 10 seconds
            self._print_progress_update()
    
    def _print_progress_update(self):
        """Print current progress status"""
        with self._lock:
            if self.stats.total_targets == 0:
                return
            
            progress = self.stats.completed / self.stats.total_targets * 100
            elapsed = self.stats.elapsed_time or timedelta(0)
            remaining = self.stats.estimated_remaining
        
        # Create progress bar
        bar_width = 30
        filled = int(bar_width * progress / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        elapsed_str = self._format_duration(elapsed)
        remaining_str = self._format_duration(remaining) if remaining else "calculating..."
        
        print(f"\r📊 [{bar}] {progress:.1f}% ({self.stats.completed}/{self.stats.total_targets}) "
              f"| ⏱️  {elapsed_str} | 🔮 {remaining_str}", end="", flush=True)
    
    def _print_final_summary(self):
        """Print comprehensive build summary"""
        print("\n\n" + "🎯 BUILD SUMMARY" + "=" * 45)
        
        # Basic stats
        print(f"📋 Total Targets:     {self.stats.total_targets}")
        print(f"✅ Completed:        {self.stats.completed}")
        print(f"❌ Failed:           {self.stats.failed}")
        print(f"⏭️  Skipped:          {self.stats.skipped}")
        print(f"📈 Success Rate:     {self.stats.success_rate:.1f}%")
        
        # Timing
        print(f"⏱️  Total Time:       {self._format_duration(self.stats.elapsed_time)}")
        
        if self.stats.target_times:
            avg_time = sum(self.stats.target_times.values()) / len(self.stats.target_times)
            fastest = min(self.stats.target_times.values())
            slowest = max(self.stats.target_times.values())
            
            print(f"🚀 Average Time:     {avg_time:.2f}s")
            print(f"⚡ Fastest Build:    {fastest:.2f}s")
            print(f"🐌 Slowest Build:    {slowest:.2f}s")
        
        # Performance analysis
        if self.stats.elapsed_time and self.stats.elapsed_time.total_seconds() > 0:
            throughput = self.stats.completed / self.stats.elapsed_time.total_seconds() * 60
            print(f"🏃 Throughput:       {throughput:.1f} targets/minute")
        
        # Final status
        if self.stats.failed == 0:
            print("\n🎉 BUILD SUCCESSFUL! All targets completed successfully.")
        else:
            print(f"\n⚠️  BUILD COMPLETED WITH {self.stats.failed} FAILURES")
        
        print("=" * 60)
    
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration in human-readable format"""
        if not duration:
            return "0s"
        
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def _format_size(self, size_bytes: Optional[int]) -> str:
        """Format file size in human-readable format"""
        if not size_bytes:
            return "unknown size"
        
        size_float = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_float < 1024.0:
                return f"{size_float:.1f}{unit}"
            size_float /= 1024.0
        return f"{size_float:.1f}TB"
    
    # Additional utility methods for general logging
    def info(self, message: str):
        """Log an info message"""
        if self._last_was_progress:
            print()  # Add newline after progress bar
            self._last_was_progress = False
        print(message)
    
    def success(self, message: str):
        """Log a success message"""
        if self._last_was_progress:
            print()  # Add newline after progress bar
            self._last_was_progress = False
        print(message)
    
    def error(self, message: str):
        """Log an error message"""
        if self._last_was_progress:
            print()  # Add newline after progress bar
            self._last_was_progress = False
        print(message)
    
    def warning(self, message: str):
        """Log a warning message"""
        if self._last_was_progress:
            print()  # Add newline after progress bar
            self._last_was_progress = False
        print(message)
    
    def update_progress(self, description: str, progress: float):
        """Update progress with description and percentage"""
        # Avoid excessive logging by only updating when progress changes significantly
        progress_key = f"{description}:{progress:.1f}"
        if hasattr(self, '_last_progress') and self._last_progress == progress_key:
            return
        
        self._last_progress = progress_key
        bar_width = 20
        filled = int(bar_width * progress / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"\r{description}: [{bar}] {progress:.1f}%", end="", flush=True)
        self._last_was_progress = True


# Singleton instance for global use
reporter = ProgressReporter()


def get_progress_reporter() -> ProgressReporter:
    """Get the global progress reporter instance"""
    return reporter
