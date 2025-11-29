import apiClient from './client';

export const getFields = async () => {
    const response = await apiClient.get('/fields');
    return response.data;
};

export const createField = async (fieldData) => {
    const response = await apiClient.post('/fields', fieldData);
    return response.data;
};

export const updateField = async (fieldId, fieldData) => {
    const response = await apiClient.put(`/fields/${fieldId}`, fieldData);
    return response.data;
};

export const deleteField = async (fieldId) => {
    const response = await apiClient.delete(`/fields/${fieldId}`);
    return response.data;
};

export const createCheckpoint = async (checkpointData) => {
    const response = await apiClient.post('/checkpoints', checkpointData);
    return response.data;
};

export const updateCheckpoint = async (checkpointId, checkpointData) => {
    const response = await apiClient.put(`/checkpoints/${checkpointId}`, checkpointData);
    return response.data;
};

export const deleteCheckpoint = async (checkpointId) => {
    const response = await apiClient.delete(`/checkpoints/${checkpointId}`);
    return response.data;
};

export const controlPump = async (pumpId, isOn) => {
    const response = await apiClient.post(`/pumps/${pumpId}/control`, { is_on: isOn });
    return response.data;
};

export const getTriggerTasks = async (fieldId = null) => {
    const config = fieldId ? { params: { field_id: fieldId } } : {};
    const response = await apiClient.get('/trigger-tasks', config);
    return response.data;
};

export const createTriggerTask = async (taskData) => {
    const response = await apiClient.post('/trigger-tasks', taskData);
    return response.data;
};

export const updateTriggerTask = async (taskId, taskData) => {
    const response = await apiClient.put(`/trigger-tasks/${taskId}`, taskData);
    return response.data;
};

export const deleteTriggerTask = async (taskId) => {
    const response = await apiClient.delete(`/trigger-tasks/${taskId}`);
    return response.data;
};

export const evaluateTriggerTask = async (taskId, weatherData) => {
    const response = await apiClient.post(`/trigger-tasks/${taskId}/evaluate`, weatherData);
    return response.data;
};
