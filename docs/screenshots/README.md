# Screenshots

Place screenshot images in this directory and reference them from the project README.

## Recommended screenshots to capture

1. **`01_control_panel.png`** — The Control Panel overlay (top-left) showing the media URL input, swarm size slider, and Launch Simulation button.
2. **`02_simulation_running.png`** — A running simulation with 1,000 agents in the 3D viewport, showing the colorful swarm mid-propagation.
3. **`03_hud_neural_signature.png`** — The HUD overlay (top-right) showing tick count, connection status, and the neural signature bar chart.
4. **`04_full_interface.png`** — Full browser window showing all three components together: ControlPanel, SwarmVisualizer, and HUD.
5. **`05_agent_states.png`** — Close-up of agents in different states (blue=Neutral, orange-red=Excited, yellow=Propagating, purple=Inhibited, grey=Exhausted).

## How to capture

1. Start the backend: `cd backend && uvicorn main:app --reload --port 8000`
2. Start the frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173`
4. Enter any URL and click Launch Simulation
5. Use your OS screenshot tool or browser DevTools to capture
