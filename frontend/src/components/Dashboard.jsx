import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getWeather } from '../api/weather';
import { getFields, getTriggerTasks, evaluateTriggerTask } from '../api/sensors';
import { useAuth } from '../contexts/AuthContext';
import WeatherDisplay from './WeatherDisplay';
import FieldsDisplay from './FieldsDisplay';
import ControlPanel from './ControlPanel';

const Dashboard = () => {
    const { user, logout } = useAuth();
    const queryClient = useQueryClient();
    const [selectedFieldId, setSelectedFieldId] = useState(null);

    const { data: fields, isLoading: fieldsLoading, dataUpdatedAt } = useQuery({
        queryKey: ['fields'],
        queryFn: getFields,
        refetchInterval: 10000,
        staleTime: 0,
        gcTime: 0,
    });

    useEffect(() => {
        if (fields && fields.length > 0 && !selectedFieldId) {
            setSelectedFieldId(fields[0].id);
        }
    }, [fields, selectedFieldId]);

    const selectedField = fields?.find((f) => f.id === selectedFieldId);
    const city = selectedField?.city || 'Dublin';

    const { data: weather, isLoading: weatherLoading } = useQuery({
        queryKey: ['weather', city],
        queryFn: () => getWeather(city),
        refetchInterval: 60000,
        enabled: !!city,
    });

    useEffect(() => {
        if (weather && selectedFieldId) {
            const evaluateTriggers = async () => {
                try {
                    const tasks = await getTriggerTasks(selectedFieldId);
                    const activeTasks = tasks.filter((task) => task.is_active);

                    console.log(`Evaluating ${activeTasks.length} active trigger(s) for field ${selectedFieldId}`);
                    console.log('Current weather:', weather);

                    for (const task of activeTasks) {
                        const weatherData = {
                            temperature: weather.temperature,
                            humidity: weather.humidity,
                            wind_speed: weather.wind_speed,
                        };

                        try {
                            const result = await evaluateTriggerTask(task.id, weatherData);
                            console.log(`Trigger ${task.id} (${task.name}):`, result);

                            if (result.triggered) {
                                queryClient.invalidateQueries(['fields']);
                            }
                        } catch (err) {
                            console.error(`Error evaluating trigger task ${task.id}:`, err);
                        }
                    }
                } catch (err) {
                    console.error('Error fetching trigger tasks:', err);
                }
            };

            evaluateTriggers();
        }
    }, [weather, selectedFieldId]);

    return (
        <div className="dashboard">
            <header className="dashboard-header">
                <h1>Plant Irrigation Dashboard</h1>
                <div className="user-info">
                    <span>Welcome, {user?.username}!</span>
                    <button onClick={logout} className="logout-button">
                        Logout
                    </button>
                </div>
            </header>

            <div className="dashboard-content">
                <div className="dashboard-left">
                    <ControlPanel
                        fields={fields}
                        selectedFieldId={selectedFieldId}
                        onFieldSelect={setSelectedFieldId}
                    />
                    <div className="dashboard-section">
                        <FieldsDisplay
                            fields={fields}
                            loading={fieldsLoading}
                            lastUpdated={dataUpdatedAt}
                        />
                    </div>
                </div>

                <div className="dashboard-right">
                    <div className="dashboard-section">
                        <WeatherDisplay
                            weather={weather}
                            loading={weatherLoading}
                            city={city}
                            fieldName={selectedField?.name}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;

