import axios from 'axios';

// In Docker, this would be empty and requests would be handled by Nginx
// In development, we need to explicitly set the backend URL
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8005';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const chatApi = {
  sendMessage: async (message, responseMode = "rag", sessionId = null, systemPrompt = null, promptStyle = "default") => {
    try {
      // Generate a random session ID if not provided
      const session_id = sessionId || `session_${Math.random().toString(36).substring(2, 15)}`;
      
      console.log(`Sending chat request with session_id: ${session_id}, mode: ${responseMode}, promptStyle: ${promptStyle}`);
      if (systemPrompt) {
        console.log(`Using custom system prompt (${systemPrompt.length} chars)`);
      }
      
      // Map UI response mode to backend mode parameter
      let mode = "rag";
      if (responseMode === "standard") {
        mode = "no_rag";
      } else if (responseMode === "compare") {
        mode = "compare";
      }
      
      // Prepare request payload, including system_prompt if provided
      const payload = { 
        message,
        session_id,
        mode,
        prompt_style: promptStyle
      };
      
      // Only include system_prompt if it's provided
      if (systemPrompt) {
        payload.system_prompt = systemPrompt;
      }
      
      const response = await api.post('/chat', payload);
      
      // Return the response data along with the session ID for future requests
      return { 
        ...response.data,
        session_id 
      };
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  },
  
  runTests: async (testData = null) => {
    try {
      // Case 1: Single prompt test with expected result
      if (testData && typeof testData === 'object' && testData.prompt) {
        const response = await api.post('/test/single', {
          prompt: testData.prompt,
          expected_result: testData.expected_result || ""
        });
        return response.data;
      }
      // Case 2: String filepath
      else if (typeof testData === 'string') {
        // Single test case with a string path
        if (!testData.includes('.csv')) {
          const response = await api.post('/test/single', { test_file: testData });
          return response.data;
        } 
        // Batch test with filepath
        else {
          const response = await api.post('/chat/batch-test', 
            { test_file: testData },
            { params: { similarity_threshold: 0.7 } }
          );
          return response.data;
        }
      }
      // Case 3: No test data (default test)
      else {
        const response = await api.post('/test/single');
        return response.data;
      }
    } catch (error) {
      console.error('Error running chat tests:', error);
      throw error;
    }
  },
  
  // New methods for long-running tests
  startBatchTest: async (file, similarityThreshold = 0.7) => {
    try {
      const formData = new FormData();
      formData.append('csv_file', file);
      
      const response = await api.post(`/test/batch/start?similarity_threshold=${similarityThreshold}`, 
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error starting batch test:', error);
      throw error;
    }
  },
  
  getTestJobStatus: async (jobId) => {
    try {
      const response = await api.get(`/test/jobs/${jobId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting test job status:', error);
      throw error;
    }
  },
  
  getAllTestJobs: async () => {
    try {
      const response = await api.get('/test/jobs');
      return response.data;
    } catch (error) {
      console.error('Error listing test jobs:', error);
      throw error;
    }
  }
};

export const indexApi = {
  // Cache Management
  clearCache: async (olderThanDays = null) => {
    try {
      const params = olderThanDays ? { older_than_days: olderThanDays } : {};
      const response = await api.delete('/chat/cache', { params });
      return response.data;
    } catch (error) {
      console.error('Error clearing cache:', error);
      throw error;
    }
  },
  
  getCacheStats: async () => {
    try {
      const response = await api.get('/chat/cache/stats');
      return response.data;
    } catch (error) {
      console.error('Error fetching cache stats:', error);
      throw error;
    }
  },
  
  // Google Drive Indexing
  indexGoogleDrive: async (folderId = null, recursive = true, enhancedSlides = false) => {
    try {
      // Send folder_id as a query parameter instead of in the request body
      const params = {};
      if (folderId) params.folder_id = folderId;
      if (recursive !== undefined) params.recursive = recursive;
      if (enhancedSlides !== undefined) params.enhanced_slides = enhancedSlides;
      
      const response = await api.post('/index/google-drive', {}, { params });
      return response.data;
    } catch (error) {
      console.error('Error indexing Google Drive:', error);
      throw error;
    }
  },
  
  listGoogleDriveFiles: async () => {
    try {
      const response = await api.get('/index/google-drive/files');
      return response.data;
    } catch (error) {
      console.error('Error listing Google Drive files:', error);
      throw error;
    }
  },
  
  // Shopify Indexing
  indexShopify: async (shopifyDomain = null) => {
    try {
      // Using the correct endpoint based on routes.py - it's just /index/
      const response = await api.post('/index/', { store: shopifyDomain });
      return response.data;
    } catch (error) {
      console.error('Error indexing Shopify:', error);
      throw error;
    }
  },
  
  listShopifyContent: async () => {
    try {
      // Using the general index info endpoint
      const response = await api.get('/index/');
      return response.data;
    } catch (error) {
      console.error('Error listing Shopify content:', error);
      throw error;
    }
  },
  
  // General index operations
  deleteDocument: async (documentId) => {
    try {
      const response = await api.delete(`/index/document/${documentId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting document:', error);
      throw error;
    }
  },
  
  healthCheck: async () => {
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }
};

export default { chatApi, indexApi };