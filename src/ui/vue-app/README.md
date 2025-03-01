# Flowchart Builder (Vue.js)

This is a refactored version of the Flowchart Builder application using Vue.js. The original application was built using vanilla JavaScript, which made the code harder to read and maintain. This refactored version uses Vue.js to improve code organization, readability, and maintainability.

## Project Structure

The application is organized into the following components:

- **App.vue**: The main application component that manages the overall state and coordinates between child components.
- **Toolbar.vue**: Handles the toolbar UI with buttons for creating nodes and managing the flowchart.
- **FlowchartCanvas.vue**: Manages the canvas where nodes and connections are rendered.
- **FlowchartNode.vue**: Represents an individual node in the flowchart.

## Key Improvements

1. **Component-Based Architecture**: The application is now organized into reusable components, making the code more modular and easier to understand.
2. **Reactive State Management**: Vue.js's reactive data system simplifies state management compared to manually updating the DOM.
3. **Declarative Templates**: HTML templates with Vue directives make the UI structure more clear and maintainable.
4. **Event Handling**: Component communication through events provides a cleaner separation of concerns.
5. **Improved Code Organization**: Logic is now distributed across components based on responsibility, rather than being in one large script file.

## Running the Application

1. Install dependencies:
   ```
   npm install
   ```

2. Start the development server:
   ```
   npm run serve
   ```

3. Build for production:
   ```
   npm run build
   ```

## API Integration

The application communicates with a Python FastAPI backend running on port 8000. The Vue.js application proxies API requests through the development server to avoid CORS issues.
