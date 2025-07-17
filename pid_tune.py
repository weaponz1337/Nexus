import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from scipy.optimize import differential_evolution
from dataclasses import dataclass
import time


# Constants
settling_tolerance = 0.005

@dataclass
class SimulationParams:
    Kp: float
    Ki: float
    Kd: float
    cv_min: float
    cv_max: float
    cv_start: float
    pv_min: float
    pv_max: float
    pv_start: float
    pv_final: float
    process_gain: float
    dead_time: float
    time_constant: float
    setpoint: float
    timestep: float

# PID Controller Class
class PID:
    # Initialize PID, set parameters and set integral and error to zero
    def __init__(self, Kp, Ki, Kd, cv_start):
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.integral = cv_start / self.Ki if self.Ki > 0 else 0.0
        self.prev_error = 0

    # Reset PID, set integral and error to zero
    def reset(self, cv_start):
        self.integral = cv_start / self.Ki if self.Ki > 0 else 0.0
        self.prev_error = 0
        
    # Core PID logic  
    def update(self, error, dt, cv_min, cv_max):
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        control = np.clip(self.Kp * error + self.Ki * self.integral + self.Kd * derivative, cv_min, cv_max)
        self.prev_error = error
        integral = self.integral
        return control, integral


# System Simulation
def simulate_system(params: SimulationParams):
    # Call the PID and make sure it's reset at the start
    pid = PID(params.Kp, params.Ki, params.Kd, params.cv_start)
    pid.reset(params.cv_start)
    
    # Initialize CV and PV based on setpoints
    pv = np.clip(params.pv_start, params.pv_min, params.pv_max)
    sp = params.setpoint
    cv = params.cv_start
    
    points_per_second = 1 / params.timestep
    if params.dead_time <= 1:
        sim_time = 20
    else:
        sim_time = params.dead_time * 20
    num_points = int(sim_time * points_per_second)
    t_eval = np.linspace(0, sim_time, num_points)


    # Fill out the cv buffer with the CV init value to avoid starting at zero
    cv_delay_steps = max(1, int(np.round(params.dead_time / params.timestep)))
    cv_buffer = [params.cv_start] * cv_delay_steps
    
    # Initialize lists for cv/pv/sp histories
    pv_array = [pv]
    cv_history = [cv]
    sp_array = [sp]
    
    # Run the actual simulation for x time
    for i, t in enumerate(t_eval[1:]):
        # Update the PID every cycle
        error = sp - pv
        cv, integral = pid.update(error, params.timestep, params.cv_min, params.cv_max)
        
        cv_buffer.append(cv)
        delayed_cv = cv_buffer.pop(0)
        # Update the PID simulation
        dpv = (-pv + params.process_gain * delayed_cv) / params.time_constant
        pv += dpv * params.timestep
        pv = np.clip(pv, params.pv_min, params.pv_max)
        
        # Add the PV, cv and SP to arrays for plotting
        pv_array.append(pv)
        cv_history.append(cv)
        sp_array.append(sp)
    return np.array(pv_array), np.array(sp_array), np.array(cv_history), np.array(t_eval)

# Compute Settling Time
def compute_settling_time(pv, t, pv_final, tolerance=settling_tolerance):
    pv = np.asarray(pv)
    t = np.asarray(t)

    min_len = min(len(pv), len(t))
    pv = pv[:min_len]
    t = t[:min_len]

    band_upper = pv_final * (1 + tolerance)
    band_lower = pv_final * (1 - tolerance)

    for i in range(min_len):
        window = pv[i:]
        if np.all((window >= band_lower) & (window <= band_upper)):
            return t[i]
    return t[-1]  # If it never settles

def truncate_float(value, decimals=2):
    factor = 10 ** decimals
    return int(value * factor) / factor

trial_counter = 0

def process_pid_tuning(kp, ki, kd, **kwargs):
    """
    Main entry point for PID tuning from Flask app
    Args:
        kp, ki, kd: PID parameters
        **kwargs: Optional simulation parameters
    Returns:
        dict: Results for template rendering
    """
    try:
        # Default simulation parameters - you can make these configurable
        params = SimulationParams(
            Kp=kp,
            Ki=ki, 
            Kd=kd,
            cv_min=kwargs.get('cv_min', 0.0),
            cv_max=kwargs.get('cv_max', 100.0),
            cv_start=kwargs.get('cv_start', 50.0),
            pv_min=kwargs.get('pv_min', 0.0),
            pv_max=kwargs.get('pv_max', 100.0),
            pv_start=kwargs.get('pv_start', 0.0),
            pv_final=kwargs.get('pv_final', 50.0),
            process_gain=kwargs.get('process_gain', 1.0),
            dead_time=kwargs.get('dead_time', 2.0),
            time_constant=kwargs.get('time_constant', 5.0),
            setpoint=kwargs.get('setpoint', 50.0),
            timestep=kwargs.get('timestep', 0.1)
        )
        
        # Run simulation
        pv_array, sp_array, cv_history, t_eval = simulate_system(params)
        
        # Calculate performance metrics
        settling_time = compute_settling_time(pv_array, t_eval, params.pv_final)
        
        # Calculate other metrics
        steady_state_error = abs(pv_array[-1] - params.setpoint)
        overshoot = max(0, (np.max(pv_array) - params.setpoint) / params.setpoint * 100)
        
        # Prepare results for template
        results = {
            'input_params': {
                'kp': truncate_float(kp),
                'ki': truncate_float(ki), 
                'kd': truncate_float(kd)
            },
            'performance_metrics': {
                'settling_time': truncate_float(settling_time),
                'steady_state_error': truncate_float(steady_state_error),
                'overshoot': truncate_float(overshoot),
                'final_pv': truncate_float(pv_array[-1])
            },
            'simulation_data': {
                'time': t_eval.tolist(),
                'pv': pv_array.tolist(),
                'setpoint': sp_array.tolist(), 
                'cv': cv_history.tolist()
            },
            'system_params': {
                'process_gain': params.process_gain,
                'dead_time': params.dead_time,
                'time_constant': params.time_constant
            }
        }
        
        return results
        
    except Exception as e:
        raise Exception(f"PID simulation failed: {str(e)}")

def optimize_pid_parameters(target_params, bounds=None):
    """
    Auto-tune PID parameters using optimization
    Args:
        target_params: dict with target performance metrics
        bounds: tuple of (min, max) for each parameter
    Returns:
        dict: Optimized PID parameters and performance
    """
    if bounds is None:
        bounds = [(0.1, 10.0), (0.01, 2.0), (0.001, 1.0)]  # Kp, Ki, Kd bounds
    
    def objective_function(params):
        kp, ki, kd = params
        try:
            results = process_pid_tuning(kp, ki, kd)
            metrics = results['performance_metrics']
            
            # Weighted objective function - customize as needed
            score = (
                metrics['settling_time'] * 0.4 +
                metrics['steady_state_error'] * 0.3 +
                metrics['overshoot'] * 0.3
            )
            return score
        except:
            return 1000  # Penalty for failed simulations
    
    # Run optimization
    result = differential_evolution(objective_function, bounds, seed=42)
    
    if result.success:
        kp_opt, ki_opt, kd_opt = result.x
        optimized_results = process_pid_tuning(kp_opt, ki_opt, kd_opt)
        
        return {
            'success': True,
            'optimized_params': {
                'kp': truncate_float(kp_opt),
                'ki': truncate_float(ki_opt),
                'kd': truncate_float(kd_opt)
            },
            'performance': optimized_results['performance_metrics'],
            'iterations': result.nit
        }
    else:
        return {'success': False, 'error': 'Optimization failed to converge'}

def generate_chart(kp, ki, kd, chart_type):
    """
    Generate chart data for different visualization types
    Args:
        kp, ki, kd: PID parameters
        chart_type: Type of chart ('response', 'bode', 'nyquist')
    Returns:
        dict: Chart data for frontend rendering
    """
    try:
        # Get simulation results
        results = process_pid_tuning(kp, ki, kd)
        
        if chart_type == 'response':
            return {
                'type': 'line',
                'data': {
                    'labels': results['simulation_data']['time'],
                    'datasets': [
                        {
                            'label': 'Process Variable',
                            'data': results['simulation_data']['pv'],
                            'borderColor': 'rgb(75, 192, 192)',
                            'fill': False
                        },
                        {
                            'label': 'Setpoint',
                            'data': results['simulation_data']['setpoint'],
                            'borderColor': 'rgb(255, 99, 132)',
                            'borderDash': [5, 5],
                            'fill': False
                        },
                        {
                            'label': 'Control Variable',
                            'data': results['simulation_data']['cv'],
                            'borderColor': 'rgb(54, 162, 235)',
                            'fill': False
                        }
                    ]
                }
            }
        elif chart_type == 'error':
            # Calculate error over time
            pv_data = results['simulation_data']['pv']
            sp_data = results['simulation_data']['setpoint']
            error_data = [sp - pv for sp, pv in zip(sp_data, pv_data)]
            
            return {
                'type': 'line',
                'data': {
                    'labels': results['simulation_data']['time'],
                    'datasets': [
                        {
                            'label': 'Control Error',
                            'data': error_data,
                            'borderColor': 'rgb(255, 159, 64)',
                            'fill': True,
                            'backgroundColor': 'rgba(255, 159, 64, 0.2)'
                        }
                    ]
                }
            }
        else:
            return {'error': f'Unknown chart type: {chart_type}'}
            
    except Exception as e:
        return {'error': str(e)}