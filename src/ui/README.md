# Flowchart Builder (Vue.js)

This is a Vue.js implementation of the Flowchart Builder application. The original vanilla JavaScript implementation has been refactored to use Vue.js for improved code organization, readability, and maintainability.

## Running the Application

To run the application, follow these steps:

1. Navigate to the Vue.js application directory:
   ```
   cd src/ui/vue-app
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm run serve
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:8080
   ```

Alternatively, you can use the provided run script:
   ```
   cd src/ui/vue-app
   ./run.sh
   ```

## Application Structure

The Vue.js application is organized into the following components:

- **App.vue**: The main application component that manages the overall state and coordinates between child components.
- **Toolbar.vue**: Handles the toolbar UI with buttons for creating nodes and managing the flowchart.
- **FlowchartCanvas.vue**: Manages the canvas where nodes and connections are rendered.
- **FlowchartNode.vue**: Represents an individual node in the flowchart.

## API Integration

The application communicates with a Python FastAPI backend running on port 8000. The Vue.js application proxies API requests through the development server to avoid CORS issues.
