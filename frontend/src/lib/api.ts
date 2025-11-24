/**
 * API Client Utility
 * Centralized API functions for communicating with the backend
 */

const API_BASE_URL = '/api';

interface ApiResponse<T = any> {
  success?: boolean;
  error?: string;
  data?: T;
  [key: string]: any;
}

/**
 * Generic API request function
 */
export class ApiError extends Error {
  status?: number;
  details?: ApiResponse;

  constructor(message: string, status?: number, details?: ApiResponse) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultOptions: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, defaultOptions);
    const data: ApiResponse<T> = await response.json();

    if (!response.ok) {
      const message = data.error
        || (Array.isArray((data as any)?.errors) ? (data as any).errors.join(', ') : undefined)
        || `HTTP error! status: ${response.status}`;
      throw new ApiError(message, response.status, data);
    }

    return data as T;
  } catch (error) {
    console.error(`API request failed: ${endpoint}`, error);
    throw error;
  }
}

/**
 * Listings API
 */
export const listingsApi = {
  getAll: (params?: { status?: string; category?: string }) => {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status', params.status);
    if (params?.category) queryParams.append('category', params.category);
    
    const query = queryParams.toString();
    return apiRequest(`/listings${query ? `?${query}` : ''}`);
  },

  getById: (listingId: string) => {
    return apiRequest(`/listings/${listingId}`);
  },

  create: (data: any) => {
    return apiRequest('/listings', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: (listingId: string, data: any) => {
    return apiRequest(`/listings/${listingId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete: (listingId: string) => {
    return apiRequest(`/listings/${listingId}`, {
      method: 'DELETE',
    });
  },

  bulkUpdate: (data: { listing_ids: string[]; status: string }) => {
    return apiRequest('/listings/bulk-update', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  bulkDelete: (data: { listing_ids: string[] }) => {
    return apiRequest('/listings/bulk-delete', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

/**
 * Research API
 */
export const researchApi = {
  compareUsJp: (data: { asin: string; us_asin?: string; exchange_rate?: number }) => {
    return apiRequest('/compare/us-jp', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  searchProduct: (data: { product_info: string; use_jan_code?: boolean }) => {
    return apiRequest('/search/product', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

/**
 * Monitoring API
 */
export const monitoringApi = {
  getStatus: () => {
    return apiRequest('/monitor/status');
  },

  checkListing: (listingId: string) => {
    return apiRequest(`/monitor/check/${listingId}`, {
      method: 'POST',
    });
  },

  checkAll: () => {
    return apiRequest('/monitor/check-all', {
      method: 'POST',
    });
  },
};

/**
 * Blacklist API
 */
export const blacklistApi = {
  getAll: () => {
    return apiRequest('/blacklist');
  },

  check: (data: { asin?: string; title?: string; manufacturer?: string; category?: string; brand?: string }) => {
    return apiRequest('/blacklist/check', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  create: (data: { type: string; value: string; reason?: string; severity?: string }) => {
    return apiRequest('/blacklist', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  delete: (entryId: string) => {
    return apiRequest(`/blacklist/${entryId}`, {
      method: 'DELETE',
    });
  },
};

/**
 * Profit & Shipping API
 */
export const calculationApi = {
  calculateProfit: (data: {
    us_price: number;
    jp_price?: number;
    shipping_cost?: number;
    exchange_rate?: number;
  }) => {
    return apiRequest('/profit/calculate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  calculateShipping: (data: {
    weight: number;
    dimensions?: string;
    destination?: string;
  }) => {
    return apiRequest('/shipping/calculate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

/**
 * Health check API
 */
export const healthApi = {
  check: () => {
    return apiRequest('/health');
  },
};

