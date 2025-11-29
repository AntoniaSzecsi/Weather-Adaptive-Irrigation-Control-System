import apiClient from './client';

export const getWeather = async (city = 'London') => {
    const response = await apiClient.get('/weather', {
        params: { city },
    });
    return response.data;
};

