const WeatherDisplay = ({ weather, loading, city, fieldName }) => {
    return (
        <div className="weather-card">
            <h2>Weather Information</h2>

            {fieldName && (
                <div className="field-info">
                    <span className="field-label">Field: {fieldName}</span>
                </div>
            )}

            {loading ? (
                <div className="loading">Loading weather data...</div>
            ) : weather ? (
                <div className="weather-info">
                    <div className="weather-main">
                        <h3>{weather.city}</h3>
                        <div className="temperature">{weather.temperature}°C</div>
                        <div className="description">{weather.description}</div>
                    </div>
                    <div className="weather-details">
                        <div className="detail-item">
                            <span className="label">Humidity:</span>
                            <span className="value">{weather.humidity}%</span>
                        </div>
                        <div className="detail-item">
                            <span className="label">Wind Speed:</span>
                            <span className="value">{weather.wind_speed} m/s</span>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="error">Failed to load weather data</div>
            )}
        </div>
    );
};

export default WeatherDisplay;

