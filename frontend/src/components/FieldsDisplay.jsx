import { useMutation, useQueryClient } from '@tanstack/react-query';
import { controlPump } from '../api/sensors';

const FieldsDisplay = ({ fields, loading, lastUpdated }) => {
    const queryClient = useQueryClient();

    const pumpMutation = useMutation({
        mutationFn: ({ pumpId, isOn }) => controlPump(pumpId, isOn),
        onSuccess: () => {
            queryClient.invalidateQueries(['fields']);
        },
    });

    const handlePumpToggle = (pumpId, currentState) => {
        pumpMutation.mutate({ pumpId, isOn: !currentState });
    };

    if (loading) {
        return (
            <div className="fields-card">
                <h2>Irrigation Fields</h2>
                <div className="loading">Loading field data...</div>
            </div>
        );
    }

    if (!fields || fields.length === 0) {
        return (
            <div className="fields-card">
                <h2>Irrigation Fields</h2>
                <div className="no-data">No field data available yet</div>
            </div>
        );
    }

    return (
        <div className="fields-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ margin: 0 }}>Irrigation Fields</h2>
                {lastUpdated && (
                    <span style={{ fontSize: '12px', color: '#666' }}>
                        Last updated: {new Date(lastUpdated).toLocaleTimeString()}
                    </span>
                )}
            </div>
            <div className="fields-grid">
                {fields.map((field) => (
                    <div key={field.id} className="field-card">
                        <h3 className="field-name">{field.name}</h3>
                        <div className="checkpoints-list">
                            {field.checkpoints.map((checkpoint) => (
                                <div key={checkpoint.id} className="checkpoint-card">
                                    <h4 className="checkpoint-name">{checkpoint.name}</h4>

                                    <div className="sensors-grid">
                                        {checkpoint.sensors && Object.entries(checkpoint.sensors).map(([type, data]) => (
                                            <div key={type} className="sensor-item">
                                                <span className="sensor-label">
                                                    {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                                                </span>
                                                <span className="sensor-value">
                                                    {data.value} {data.unit}
                                                </span>
                                            </div>
                                        ))}
                                    </div>

                                    {checkpoint.pump && (
                                        <div className="pump-control">
                                            <div className="pump-info">
                                                <span className="pump-name">{checkpoint.pump.name}</span>
                                                <span className={`pump-status ${checkpoint.pump.is_on ? 'on' : 'off'}`}>
                                                    {checkpoint.pump.is_on ? 'ON' : 'OFF'}
                                                </span>
                                            </div>
                                            <button
                                                className={`pump-button ${checkpoint.pump.is_on ? 'on' : 'off'}`}
                                                onClick={() => handlePumpToggle(checkpoint.pump.id, checkpoint.pump.is_on)}
                                                disabled={pumpMutation.isPending}
                                            >
                                                {pumpMutation.isPending
                                                    ? '...'
                                                    : checkpoint.pump.is_on
                                                        ? 'Turn Off'
                                                        : 'Turn On'}
                                            </button>
                                            {checkpoint.pump.last_activated && (
                                                <div className="pump-last-activated">
                                                    Last activated: {new Date(checkpoint.pump.last_activated).toLocaleString()}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default FieldsDisplay;

