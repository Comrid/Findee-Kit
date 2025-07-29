/*
 * CONTENTS
 * ========
 * GridStack Initialization
 * Widget Management
 * Sample Widgets
 */

// Initialize GridStack
function initializeGridStack() {
    const grid = GridStack.init({
        float: true,
        cellHeight: 100,
        margin: '10px',
        disableOneColumnMode: true
    });
    
    // Store grid instance globally
    window.gridStack = grid;
    
    return grid;
}

// Add sample widgets
function addSampleWidgets(grid) {
    // CPU Usage Widget
    grid.addWidget({
        x: 0, y: 0, w: 6, h: 4,
        content: `
            <div class="widget-content">
                <div class="widget-header">
                    <h4><i class="fas fa-chart-line"></i> CPU Usage</h4>
                    <div class="widget-controls">
                        <button class="btn-icon"><i class="fas fa-cog"></i></button>
                        <button class="btn-icon"><i class="fas fa-times"></i></button>
                    </div>
                </div>
                <div class="widget-body">
                    <div class="gauge-widget">
                        <div class="gauge">
                            <div class="gauge-value">75%</div>
                            <div class="gauge-label">CPU Usage</div>
                        </div>
                    </div>
                </div>
            </div>
        `
    });
    
    // Memory Widget
    grid.addWidget({
        x: 6, y: 0, w: 6, h: 4,
        content: `
            <div class="widget-content">
                <div class="widget-header">
                    <h4><i class="fas fa-memory"></i> Memory</h4>
                    <div class="widget-controls">
                        <button class="btn-icon"><i class="fas fa-cog"></i></button>
                        <button class="btn-icon"><i class="fas fa-times"></i></button>
                    </div>
                </div>
                <div class="widget-body">
                    <div class="text-widget">
                        <div class="text-value">2.4 GB</div>
                        <div class="text-label">Used Memory</div>
                    </div>
                </div>
            </div>
        `
    });
}

// Initialize GridStack when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const grid = initializeGridStack();
    addSampleWidgets(grid);
});
