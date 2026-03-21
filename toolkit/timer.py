import time
from collections import OrderedDict, deque
import sys
import os

# check if is ui process will have IS_AI_TOOLKIT_UI in env
is_ui = os.environ.get("IS_AI_TOOLKIT_UI", "0") == "1"

class Timer:
    def __init__(self, name='Timer', max_buffer=10):
        self.name = name
        self.max_buffer = max_buffer
        self.timers = OrderedDict()
        self.active_timers = {}
        self.current_timer = None  # Used for the context manager functionality
        self._after_print_hooks = []

    def start(self, timer_name):
        if timer_name not in self.timers:
            self.timers[timer_name] = deque(maxlen=self.max_buffer)
        self.active_timers[timer_name] = time.time()

    def cancel(self, timer_name):
        """Cancel an active timer."""
        if timer_name in self.active_timers:
            del self.active_timers[timer_name]

    def stop(self, timer_name):
        if timer_name not in self.active_timers:
            raise ValueError(f"Timer '{timer_name}' was not started!")

        elapsed_time = time.time() - self.active_timers[timer_name]
        self.timers[timer_name].append(elapsed_time)

        # Clean up active timers
        del self.active_timers[timer_name]

        # Check if this timer's buffer exceeds max_buffer and remove the oldest if it does
        if len(self.timers[timer_name]) > self.max_buffer:
            self.timers[timer_name].popleft()

    def add_after_print_hook(self, hook):
        self._after_print_hooks.append(hook)

    def print(self):
        if not is_ui:
            print(f"\nTimer '{self.name}':")
        timing_dict = {}
        # sort by longest at top
        for timer_name, timings in sorted(self.timers.items(), key=lambda x: sum(x[1]), reverse=True):
            avg_time = sum(timings) / len(timings)
            
            if not is_ui:
                print(f" - {avg_time:.4f}s avg - {timer_name}, num = {len(timings)}")
            timing_dict[timer_name] = avg_time

        for hook in self._after_print_hooks:
            hook(timing_dict)
        if not is_ui:
            print('')

    def reset(self):
        self.timers.clear()
        self.active_timers.clear()

    def __call__(self, timer_name):
        """Enable the use of the Timer class as a context manager."""
        self.current_timer = timer_name
        self.start(timer_name)
        return self

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            # No exceptions, stop the timer normally
            self.stop(self.current_timer)
        else:
            # There was an exception, cancel the timer
            self.cancel(self.current_timer)


class PhaseTimer:
    """Records wall-clock durations for one-shot training phases."""

    def __init__(self):
        self.phases = OrderedDict()
        self._active = None

    def start(self, name):
        self._active = name
        self.phases[name] = {'start': time.time(), 'end': None, 'duration': None}

    def stop(self, name=None):
        name = name or self._active
        if name and name in self.phases and self.phases[name]['end'] is None:
            self.phases[name]['end'] = time.time()
            self.phases[name]['duration'] = self.phases[name]['end'] - self.phases[name]['start']
        self._active = None

    def __call__(self, name):
        self._active = name
        return self

    def __enter__(self):
        self.start(self._active)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def print_summary(self):
        total = sum(p['duration'] for p in self.phases.values() if p['duration'] is not None)
        print("\n" + "=" * 70)
        print("  Training Phase Summary")
        print("=" * 70)
        for name, data in self.phases.items():
            if data['duration'] is not None:
                dur = data['duration']
                pct = (dur / total * 100) if total > 0 else 0
                if dur >= 60:
                    print(f"  {name:30s}: {dur:8.1f}s ({dur/60:.1f}min)  ({pct:5.1f}%)")
                else:
                    print(f"  {name:30s}: {dur:8.1f}s            ({pct:5.1f}%)")
        print(f"  {'TOTAL':30s}: {total:8.1f}s ({total/60:.1f}min)")
        print("=" * 70 + "\n")
