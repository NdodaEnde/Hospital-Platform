document.getElementById('createDashboardForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const dashboardName = document.getElementById('dashboardName').value;

    const dashboardConfig = {
        name: dashboardName
    };

    try {
        const response = await fetch('/create-dashboard', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dashboardConfig)
        });

        if (response.ok) {
            const data = await response.json();
            const dashboardId = data.dashboardId;
            console.log('Dashboard created successfully. ID:', dashboardId);
            // Redirect the user to the dashboard view page or update the UI as needed
        } else {
            console.error('Error creating dashboard:', response.statusText);
            // Display an error message to the user
        }
    } catch (error) {
        console.error('Error creating dashboard:', error);
        // Display an error message to the user
    }
});