// Load QuickSight dashboard
async function loadQuickSightDashboard() {
    try {
      const embedUrl = await getQuickSightEmbedUrl(dashboardId);
      const quicksightDashboard = document.getElementById('quicksight-dashboard');
      quicksightDashboard.innerHTML = `<iframe src="${embedUrl}" width="100%" height="600"></iframe>`;
    } catch (error) {
      console.error('Error loading QuickSight dashboard:', error);
    }
  }
  
  // Function to fetch the embed URL for a QuickSight dashboard
  async function getQuickSightEmbedUrl(dashboardId) {
    try {
      const response = await fetch(`/quicksight-embed-url?dashboard_id=${dashboardId}`);
      if (!response.ok) {
        throw new Error('Failed to get QuickSight embed URL');
      }
      const data = await response.json();
      return data.embed_url;
    } catch (error) {
      console.error('Error:', error);
      throw error;
    }
  }
  
  // Fetch user's dashboards
  async function fetchUserDashboards() {
    try {
      const response = await fetch('/user-dashboards');
      if (response.ok) {
        const data = await response.json();
        const dashboards = data.dashboards;
        const dashboardList = document.getElementById('dashboardList');
        dashboards.forEach(dashboard => {
          const dashboardElement = document.createElement('div');
          dashboardElement.textContent = dashboard.name;
          dashboardElement.addEventListener('click', () => {
            // Embed the selected dashboard
            embedDashboard(dashboard.id);
          });
          dashboardList.appendChild(dashboardElement);
        });
      } else {
        console.error('Error fetching user dashboards:', response.statusText);
      }
    } catch (error) {
      console.error('Error fetching user dashboards:', error);
    }
  }
  
  // Function to embed a dashboard
  async function embedDashboard(dashboardId) {
    try {
      const response = await fetch(`/quicksight-embed-url?dashboard_id=${dashboardId}`);
      if (response.ok) {
        const data = await response.json();
        const embedUrl = data.embed_url;
        const dashboardEmbed = document.getElementById('dashboardEmbed');
        dashboardEmbed.innerHTML = `<iframe src="${embedUrl}" width="100%" height="600"></iframe>`;
      } else {
        console.error('Error embedding dashboard:', response.statusText);
      }
    } catch (error) {
      console.error('Error embedding dashboard:', error);
    }
  }
  
  // Fetch user's dashboards when the page loads
  fetchUserDashboards();
  
  // Load the QuickSight dashboard when the page loads
  loadQuickSightDashboard();