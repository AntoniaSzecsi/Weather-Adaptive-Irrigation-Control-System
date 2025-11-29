import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    createField,
    updateField,
    deleteField,
    createCheckpoint,
    updateCheckpoint,
    deleteCheckpoint,
    getTriggerTasks,
    createTriggerTask,
    updateTriggerTask,
    deleteTriggerTask,
    evaluateTriggerTask,
} from '../api/sensors';
import { getWeather } from '../api/weather';

const ControlPanel = ({ fields, selectedFieldId, onFieldSelect }) => {
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState('fields');
    const [editingField, setEditingField] = useState(null);
    const [editingCheckpoint, setEditingCheckpoint] = useState(null);
    const [editingTrigger, setEditingTrigger] = useState(null);
    const [showFieldForm, setShowFieldForm] = useState(false);
    const [showCheckpointForm, setShowCheckpointForm] = useState(false);
    const [showTriggerForm, setShowTriggerForm] = useState(false);

    const { data: triggerTasks = [] } = useQuery({
        queryKey: ['trigger-tasks', selectedFieldId],
        queryFn: () => getTriggerTasks(selectedFieldId),
        enabled: activeTab === 'triggers',
    });

    const selectedField = fields?.find((f) => f.id === selectedFieldId);

    const handleTestTrigger = async (task) => {
        if (!selectedField) {
            alert('Please select a field first');
            return;
        }

        try {
            // Get current weather for the field's city
            const weather = await getWeather(selectedField.city);
            const weatherData = {
                temperature: weather.temperature,
                humidity: weather.humidity,
                wind_speed: weather.wind_speed,
            };

            const result = await evaluateTriggerTask(task.id, weatherData);

            if (result.triggered) {
                alert(`✅ Trigger fired! ${result.message}\nWeather value: ${result.weather_value}, Threshold: ${result.threshold}`);
                queryClient.invalidateQueries(['fields']);
            } else {
                alert(`❌ Trigger condition not met.\nWeather value: ${result.weather_value}, Threshold: ${result.threshold}\n${result.message}`);
            }
        } catch (err) {
            console.error('Error testing trigger:', err);
            alert(`Error testing trigger: ${err.message || 'Unknown error'}`);
        }
    };

    // Field mutations
    const createFieldMutation = useMutation({
        mutationFn: createField,
        onSuccess: () => {
            queryClient.invalidateQueries(['fields']);
            setShowFieldForm(false);
        },
    });

    const updateFieldMutation = useMutation({
        mutationFn: ({ id, data }) => updateField(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries(['fields']);
            setEditingField(null);
        },
    });

    const deleteFieldMutation = useMutation({
        mutationFn: deleteField,
        onSuccess: () => {
            queryClient.invalidateQueries(['fields']);
        },
    });

    // Checkpoint mutations
    const createCheckpointMutation = useMutation({
        mutationFn: createCheckpoint,
        onSuccess: () => {
            queryClient.invalidateQueries(['fields']);
            setShowCheckpointForm(false);
        },
    });

    const updateCheckpointMutation = useMutation({
        mutationFn: ({ id, data }) => updateCheckpoint(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries(['fields']);
            setEditingCheckpoint(null);
        },
    });

    const deleteCheckpointMutation = useMutation({
        mutationFn: deleteCheckpoint,
        onSuccess: () => {
            queryClient.invalidateQueries(['fields']);
        },
    });

    // Trigger mutations
    const createTriggerMutation = useMutation({
        mutationFn: createTriggerTask,
        onSuccess: () => {
            queryClient.invalidateQueries(['trigger-tasks']);
            setShowTriggerForm(false);
        },
    });

    const updateTriggerMutation = useMutation({
        mutationFn: ({ id, data }) => updateTriggerTask(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries(['trigger-tasks']);
            setEditingTrigger(null);
        },
    });

    const deleteTriggerMutation = useMutation({
        mutationFn: deleteTriggerTask,
        onSuccess: () => {
            queryClient.invalidateQueries(['trigger-tasks']);
        },
    });

    const handleFieldSubmit = (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name'),
            city: formData.get('city'),
        };

        if (editingField) {
            updateFieldMutation.mutate({ id: editingField.id, data });
        } else {
            createFieldMutation.mutate(data);
        }
        e.target.reset();
    };

    const handleCheckpointSubmit = (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name'),
            field_id: parseInt(formData.get('field_id')),
        };

        if (editingCheckpoint) {
            updateCheckpointMutation.mutate({ id: editingCheckpoint.id, data });
        } else {
            createCheckpointMutation.mutate(data);
        }
        e.target.reset();
    };

    const handleTriggerSubmit = (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name'),
            field_id: parseInt(formData.get('field_id')),
            weather_metric: formData.get('weather_metric'),
            condition: formData.get('condition'),
            threshold: parseFloat(formData.get('threshold')),
            action: formData.get('action'),
            is_active: formData.get('is_active') === 'true',
        };

        if (editingTrigger) {
            updateTriggerMutation.mutate({ id: editingTrigger.id, data });
        } else {
            createTriggerMutation.mutate(data);
        }
        e.target.reset();
    };

    return (
        <div className="control-panel">
            <div className="control-panel-header">
                <h2>Control Panel</h2>
                <div className="tab-buttons">
                    <button
                        className={activeTab === 'fields' ? 'active' : ''}
                        onClick={() => setActiveTab('fields')}
                    >
                        Fields
                    </button>
                    <button
                        className={activeTab === 'checkpoints' ? 'active' : ''}
                        onClick={() => setActiveTab('checkpoints')}
                    >
                        Checkpoints
                    </button>
                    <button
                        className={activeTab === 'triggers' ? 'active' : ''}
                        onClick={() => setActiveTab('triggers')}
                    >
                        Triggers
                    </button>
                </div>
            </div>

            <div className="control-panel-content">
                {activeTab === 'fields' && (
                    <div className="tab-content">
                        <div className="section-header">
                            <h3>Fields Management</h3>
                            <button
                                className="add-button"
                                onClick={() => {
                                    setEditingField(null);
                                    setShowFieldForm(!showFieldForm);
                                }}
                            >
                                {showFieldForm ? 'Cancel' : '+ Add Field'}
                            </button>
                        </div>

                        {showFieldForm && (
                            <form onSubmit={handleFieldSubmit} className="form-card">
                                <h4>{editingField ? 'Edit Field' : 'Create Field'}</h4>
                                <div className="form-group">
                                    <label>Name:</label>
                                    <input
                                        type="text"
                                        name="name"
                                        required
                                        defaultValue={editingField?.name}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>City:</label>
                                    <input
                                        type="text"
                                        name="city"
                                        required
                                        defaultValue={editingField?.city || 'Dublin'}
                                    />
                                </div>
                                <button type="submit" className="submit-button">
                                    {editingField ? 'Update' : 'Create'}
                                </button>
                            </form>
                        )}

                        <div className="items-list">
                            {fields?.map((field) => (
                                <div key={field.id} className="item-card">
                                    <div className="item-header">
                                        <h4>{field.name}</h4>
                                        <span className="item-city">📍 {field.city}</span>
                                    </div>
                                    <div className="item-actions">
                                        <button
                                            className="edit-button"
                                            onClick={() => {
                                                setEditingField(field);
                                                setShowFieldForm(true);
                                            }}
                                        >
                                            Edit
                                        </button>
                                        <button
                                            className="delete-button"
                                            onClick={() => {
                                                if (window.confirm(`Delete field "${field.name}"?`)) {
                                                    deleteFieldMutation.mutate(field.id);
                                                }
                                            }}
                                        >
                                            Delete
                                        </button>
                                        <button
                                            className="select-button"
                                            onClick={() => onFieldSelect(field.id)}
                                        >
                                            {selectedFieldId === field.id ? 'Selected' : 'Select'}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {activeTab === 'checkpoints' && (
                    <div className="tab-content">
                        <div className="section-header">
                            <h3>Checkpoints Management</h3>
                            <button
                                className="add-button"
                                onClick={() => {
                                    setEditingCheckpoint(null);
                                    setShowCheckpointForm(!showCheckpointForm);
                                }}
                            >
                                {showCheckpointForm ? 'Cancel' : '+ Add Checkpoint'}
                            </button>
                        </div>

                        {showCheckpointForm && (
                            <form onSubmit={handleCheckpointSubmit} className="form-card">
                                <h4>{editingCheckpoint ? 'Edit Checkpoint' : 'Create Checkpoint'}</h4>
                                <div className="form-group">
                                    <label>Name:</label>
                                    <input
                                        type="text"
                                        name="name"
                                        required
                                        defaultValue={editingCheckpoint?.name}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Field:</label>
                                    <select name="field_id" required defaultValue={selectedFieldId || ''}>
                                        <option value="">Select Field</option>
                                        {fields?.map((field) => (
                                            <option key={field.id} value={field.id}>
                                                {field.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <button type="submit" className="submit-button">
                                    {editingCheckpoint ? 'Update' : 'Create'}
                                </button>
                            </form>
                        )}

                        <div className="items-list">
                            {fields?.map((field) =>
                                field.checkpoints?.map((checkpoint) => (
                                    <div key={checkpoint.id} className="item-card">
                                        <div className="item-header">
                                            <h4>{checkpoint.name}</h4>
                                            <span className="item-field">Field: {field.name}</span>
                                        </div>
                                        <div className="item-actions">
                                            <button
                                                className="edit-button"
                                                onClick={() => {
                                                    setEditingCheckpoint(checkpoint);
                                                    setShowCheckpointForm(true);
                                                }}
                                            >
                                                Edit
                                            </button>
                                            <button
                                                className="delete-button"
                                                onClick={() => {
                                                    if (
                                                        window.confirm(
                                                            `Delete checkpoint "${checkpoint.name}"?`
                                                        )
                                                    ) {
                                                        deleteCheckpointMutation.mutate(checkpoint.id);
                                                    }
                                                }}
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

                {activeTab === 'triggers' && (
                    <div className="tab-content">
                        <div className="section-header">
                            <h3>Trigger Tasks</h3>
                            <button
                                className="add-button"
                                onClick={() => {
                                    setEditingTrigger(null);
                                    setShowTriggerForm(!showTriggerForm);
                                }}
                            >
                                {showTriggerForm ? 'Cancel' : '+ Add Trigger'}
                            </button>
                        </div>

                        {showTriggerForm && (
                            <form onSubmit={handleTriggerSubmit} className="form-card">
                                <h4>{editingTrigger ? 'Edit Trigger' : 'Create Trigger'}</h4>
                                <div className="form-group">
                                    <label>Name:</label>
                                    <input
                                        type="text"
                                        name="name"
                                        required
                                        defaultValue={editingTrigger?.name}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Field:</label>
                                    <select
                                        name="field_id"
                                        required
                                        defaultValue={editingTrigger?.field_id || selectedFieldId || ''}
                                    >
                                        <option value="">Select Field</option>
                                        {fields?.map((field) => (
                                            <option key={field.id} value={field.id}>
                                                {field.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>Weather Metric:</label>
                                    <select
                                        name="weather_metric"
                                        required
                                        defaultValue={editingTrigger?.weather_metric}
                                    >
                                        <option value="temperature">Temperature</option>
                                        <option value="humidity">Humidity</option>
                                        <option value="wind_speed">Wind Speed</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>Condition:</label>
                                    <select
                                        name="condition"
                                        required
                                        defaultValue={editingTrigger?.condition}
                                    >
                                        <option value="greater_than">Greater Than</option>
                                        <option value="less_than">Less Than</option>
                                        <option value="equals">Equals</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>Threshold:</label>
                                    <input
                                        type="number"
                                        name="threshold"
                                        step="0.1"
                                        required
                                        defaultValue={editingTrigger?.threshold}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Action:</label>
                                    <select name="action" required defaultValue={editingTrigger?.action}>
                                        <option value="power_on_all_pumps">Power On All Pumps</option>
                                        <option value="power_off_all_pumps">Power Off All Pumps</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>Active:</label>
                                    <select
                                        name="is_active"
                                        required
                                        defaultValue={editingTrigger?.is_active !== false ? 'true' : 'false'}
                                    >
                                        <option value="true">Yes</option>
                                        <option value="false">No</option>
                                    </select>
                                </div>
                                <button type="submit" className="submit-button">
                                    {editingTrigger ? 'Update' : 'Create'}
                                </button>
                            </form>
                        )}

                        <div className="items-list">
                            {triggerTasks.map((task) => (
                                <div key={task.id} className="item-card trigger-card">
                                    <div className="item-header">
                                        <h4>{task.name}</h4>
                                        <span
                                            className={`status-badge ${task.is_active ? 'active' : 'inactive'}`}
                                        >
                                            {task.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </div>
                                    <div className="trigger-details">
                                        <p>
                                            <strong>Field:</strong>{' '}
                                            {fields?.find((f) => f.id === task.field_id)?.name}
                                        </p>
                                        <p>
                                            <strong>Condition:</strong> When {task.weather_metric} is{' '}
                                            {task.condition === 'greater_than' ? '>' : task.condition === 'less_than' ? '<' : '='}{' '}
                                            {task.threshold}
                                        </p>
                                        <p>
                                            <strong>Action:</strong>{' '}
                                            {task.action === 'power_on_all_pumps'
                                                ? 'Power On All Pumps'
                                                : 'Power Off All Pumps'}
                                        </p>
                                        {task.last_triggered && (
                                            <p className="last-triggered">
                                                Last triggered: {new Date(task.last_triggered).toLocaleString()}
                                            </p>
                                        )}
                                    </div>
                                    <div className="item-actions">
                                        <button
                                            className="test-button"
                                            onClick={() => handleTestTrigger(task)}
                                            title="Test this trigger with current weather"
                                        >
                                            Test
                                        </button>
                                        <button
                                            className="edit-button"
                                            onClick={() => {
                                                setEditingTrigger(task);
                                                setShowTriggerForm(true);
                                            }}
                                        >
                                            Edit
                                        </button>
                                        <button
                                            className="delete-button"
                                            onClick={() => {
                                                if (window.confirm(`Delete trigger "${task.name}"?`)) {
                                                    deleteTriggerMutation.mutate(task.id);
                                                }
                                            }}
                                        >
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ControlPanel;

