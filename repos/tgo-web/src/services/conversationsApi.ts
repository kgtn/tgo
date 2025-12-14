/**
 * Conversations API Service
 * Handles conversation list API endpoints (my conversations, waiting conversations)
 */

import { BaseApiService } from './base/BaseApiService';
import type { WuKongIMConversationSyncResponse, WuKongIMConversationPaginatedResponse } from '@/types';

/**
 * Response for waiting queue count
 * API may return { count: number } or { waiting: number }
 */
export interface WaitingQueueCountResponse {
  count?: number;
  waiting?: number;
}

/**
 * Response for accepting a visitor from queue
 */
export interface AcceptVisitorResponse {
  success: boolean;
  message: string;
  entry_id: string;
  visitor_id: string;
  staff_id: string;
  channel_id?: string;
  channel_type?: number;
  wait_duration_seconds?: number;
}

/**
 * Conversations API Service Class
 */
class ConversationsApiServiceClass extends BaseApiService {
  protected readonly apiVersion = 'v1';
  protected readonly endpoints = {
    MY_CONVERSATIONS: `/${this.apiVersion}/conversations/my`,
    WAITING_CONVERSATIONS: `/${this.apiVersion}/conversations/waiting`,
    ALL_CONVERSATIONS: `/${this.apiVersion}/conversations/all`,
    WAITING_QUEUE_COUNT: `/${this.apiVersion}/visitor-waiting-queue/count`,
    ACCEPT_VISITOR: `/${this.apiVersion}/visitor-waiting-queue/accept`,
  } as const;

  /**
   * Get my conversations (currently handling by this staff)
   * @param msgCount - Number of recent messages per conversation (default: 20, max: 100)
   * @returns Promise with conversation sync response
   */
  async getMyConversations(msgCount: number = 1): Promise<WuKongIMConversationSyncResponse> {
    try {
      const endpoint = `${this.endpoints.MY_CONVERSATIONS}`;
      return await this.post<WuKongIMConversationSyncResponse>(endpoint, {msg_count: msgCount});
    } catch (error) {
      console.error('Failed to fetch my conversations:', error);
      throw new Error(this['handleApiError'](error));
    }
  }

  /**
   * Get waiting visitors' conversations (unassigned)
   * @param msgCount - Number of recent messages per conversation (default: 20, max: 100)
   * @param limit - Number of conversations per page (default: 20, max: 100)
   * @param offset - Number of conversations to skip (default: 0)
   * @returns Promise with paginated conversation response
   */
  async getWaitingConversations(msgCount: number = 20, limit: number = 20, offset: number = 0): Promise<WuKongIMConversationPaginatedResponse> {
    try {
      const endpoint = `${this.endpoints.WAITING_CONVERSATIONS}?msg_count=${msgCount}&limit=${limit}&offset=${offset}`;
      return await this.post<WuKongIMConversationPaginatedResponse>(endpoint, {});
    } catch (error) {
      console.error('Failed to fetch waiting conversations:', error);
      throw new Error(this['handleApiError'](error));
    }
  }

  /**
   * Get all conversations (all visitors this staff has served)
   * @param msgCount - Number of recent messages per conversation (default: 20, max: 100)
   * @param limit - Number of conversations per page (default: 20, max: 100)
   * @param offset - Number of conversations to skip (default: 0)
   * @returns Promise with paginated conversation response
   */
  async getAllConversations(msgCount: number = 20, limit: number = 20, offset: number = 0): Promise<WuKongIMConversationPaginatedResponse> {
    try {
      const endpoint = `${this.endpoints.ALL_CONVERSATIONS}?msg_count=${msgCount}&limit=${limit}&offset=${offset}`;
      return await this.post<WuKongIMConversationPaginatedResponse>(endpoint, {});
    } catch (error) {
      console.error('Failed to fetch all conversations:', error);
      throw new Error(this['handleApiError'](error));
    }
  }

  /**
   * Get waiting queue count (unassigned visitors count)
   * @returns Promise with count response
   */
  async getWaitingQueueCount(): Promise<WaitingQueueCountResponse> {
    try {
      return await this.get<WaitingQueueCountResponse>(this.endpoints.WAITING_QUEUE_COUNT);
    } catch (error) {
      console.error('Failed to fetch waiting queue count:', error);
      throw new Error(this['handleApiError'](error));
    }
  }

  /**
   * Accept a visitor from the waiting queue
   * @param visitorId - The visitor ID to accept
   * @returns Promise with accept response
   */
  async acceptVisitor(visitorId: string): Promise<AcceptVisitorResponse> {
    try {
      return await this.post<AcceptVisitorResponse>(this.endpoints.ACCEPT_VISITOR, {
        visitor_id: visitorId,
      });
    } catch (error) {
      console.error('Failed to accept visitor:', error);
      throw new Error(this['handleApiError'](error));
    }
  }
}

// Export singleton instance
export const conversationsApi = new ConversationsApiServiceClass();
