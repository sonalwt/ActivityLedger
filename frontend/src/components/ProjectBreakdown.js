import React, { useState, useEffect } from 'react';
import { Briefcase, Clock, Calendar, ChevronRight, FolderOpen } from 'lucide-react';

const ProjectBreakdown = ({ developerId, dateRange }) => {
  const [projectData, setProjectData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedProject, setExpandedProject] = useState(null);
  
  const API_BASE = process.env.REACT_APP_API_URL || '';

  useEffect(() => {
    fetchProjectData();
  }, [developerId, dateRange]);

  const fetchProjectData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (dateRange?.start) params.append('start_date', dateRange.start);
      if (dateRange?.end) params.append('end_date', dateRange.end);
      
      const response = await fetch(
        `${API_BASE}/api/developer/${developerId}/project-breakdown?${params}`, 
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setProjectData(data);
    } catch (error) {
      setError(error.message);
      console.error('Error fetching project data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getProjectColor = (index) => {
    const colors = [
      'bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500',
      'bg-pink-500', 'bg-teal-500', 'bg-indigo-500', 'bg-red-500'
    ];
    return colors[index % colors.length];
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-red-600">Error loading project data: {error}</div>
      </div>
    );
  }

  if (!projectData || !projectData.projects) {
    return null;
  }

  const { summary, projects, project_applications } = projectData;

  return (
    <div className="space-y-6">
      {/* Project Summary */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Briefcase className="w-5 h-5 text-blue-600" />
          Project Summary
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Total Projects</div>
            <div className="text-2xl font-bold text-gray-800">
              {summary.total_projects}
            </div>
          </div>
          
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Total Hours</div>
            <div className="text-2xl font-bold text-blue-600">
              {summary.total_hours}h
            </div>
          </div>
          
          <div className="bg-green-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Most Active</div>
            <div className="text-lg font-bold text-green-600 truncate">
              {summary.most_active_project || 'N/A'}
            </div>
          </div>
        </div>

        {/* Project Distribution Chart */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-700 mb-3">Hours by Project</div>
          {projects.map((project, index) => (
            <div key={index} className="space-y-2">
              <div 
                className="flex items-center justify-between cursor-pointer hover:bg-gray-50 p-2 rounded"
                onClick={() => setExpandedProject(
                  expandedProject === project.project_name ? null : project.project_name
                )}
              >
                <div className="flex items-center gap-2 flex-1">
                  <ChevronRight 
                    className={`w-4 h-4 text-gray-400 transition-transform ${
                      expandedProject === project.project_name ? 'rotate-90' : ''
                    }`} 
                  />
                  <FolderOpen className={`w-4 h-4 ${getProjectColor(index).replace('bg-', 'text-')}`} />
                  <span className="font-medium text-sm">{project.project_name}</span>
                </div>
                
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-600">{project.total_hours}h</span>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                    {project.percentage}%
                  </span>
                </div>
              </div>
              
              <div className="ml-2">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`${getProjectColor(index)} h-2 rounded-full transition-all duration-300`}
                    style={{ width: `${project.percentage}%` }}
                  ></div>
                </div>
              </div>

              {/* Expanded Project Details */}
              {expandedProject === project.project_name && (
                <div className="ml-8 mt-2 p-3 bg-gray-50 rounded-lg">
                  <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                    <div>
                      <span className="text-gray-500">Days Worked:</span>
                      <span className="ml-2 font-medium">{project.days_worked}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Apps Used:</span>
                      <span className="ml-2 font-medium">{project.apps_used}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Avg Hours/Day:</span>
                      <span className="ml-2 font-medium">{project.average_hours_per_day}h</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Activities:</span>
                      <span className="ml-2 font-medium">{project.activity_count}</span>
                    </div>
                  </div>
                  
                  {/* Top Applications for Project */}
                  {project_applications[project.project_name] && (
                    <div className="mt-3">
                      <div className="text-xs font-medium text-gray-700 mb-2">Top Applications</div>
                      <div className="space-y-1">
                        {project_applications[project.project_name].slice(0, 5).map((app, appIndex) => (
                          <div key={appIndex} className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full"></div>
                              <span>{app.application}</span>
                              <span className="text-gray-500">({app.category})</span>
                            </div>
                            <span className="text-gray-600">{app.hours}h</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Recent Project Activity */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-blue-600" />
          Recent Project Timeline
        </h3>
        
        <div className="space-y-3">
          {Object.entries(projectData.daily_distribution)
            .slice(0, 5)
            .map(([date, projects]) => (
              <div key={date} className="border-l-2 border-gray-200 pl-4 ml-2">
                <div className="text-sm font-medium text-gray-700 mb-2">
                  {new Date(date).toLocaleDateString('en-US', { 
                    weekday: 'long', 
                    month: 'short', 
                    day: 'numeric' 
                  })}
                </div>
                <div className="space-y-1">
                  {projects.map((proj, index) => (
                    <div key={index} className="flex items-center gap-2 text-sm">
                      <div className={`w-2 h-2 ${getProjectColor(index)} rounded-full`}></div>
                      <span className="text-gray-600">{proj.project}:</span>
                      <span className="font-medium">{proj.hours}h</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
};

export default ProjectBreakdown;
