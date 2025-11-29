const SensorsDisplay = ({ sensors, loading }) => {
    if (loading) {
        return (
            <div className="sensors-card">
                <h2>Your Sensors</h2>
                <div className="loading">Loading sensor data...</div>
            </div>
        );
    }

    if (!sensors || sensors.length === 0) {
        return (
            <div className="sensors-card">
                <h2>Your Sensors</h2>
                <div className="no-data">No sensor data available yet</div>
            </div>
        );
    }

    const groupedSensors = sensors.reduce((acc, sensor) => {
        if (!acc[sensor.sensor_type]) {
            acc[sensor.sensor_type] = [];
        }
        acc[sensor.sensor_type].push(sensor);
        return acc;
    }, {});

    return (
        <div className="sensors-card">
            <h2>Your Sensors</h2>
            <div className="sensors-grid">
                {Object.entries(groupedSensors).map(([type, typeSensors]) => (
                    <div key={type} className="sensor-group">
                        <h3 className="sensor-type-title">{type.charAt(0).toUpperCase() + type.slice(1)} Sensors</h3>
                        <div className="sensor-list">
                            {typeSensors.slice(-5).map((sensor) => (
                                <div key={sensor.id} className="sensor-item">
                                    <div className="sensor-name">{sensor.name}</div>
                                    <div className="sensor-value">
                                        {sensor.value} {sensor.unit}
                                    </div>
                                    <div className="sensor-time">
                                        {new Date(sensor.timestamp).toLocaleString()}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default SensorsDisplay;

