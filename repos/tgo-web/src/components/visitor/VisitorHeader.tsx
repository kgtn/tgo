import React, { useMemo, useCallback } from 'react';
import { Camera } from 'lucide-react';
import { hasValidAvatar, generateDefaultAvatar } from '@/utils/avatarUtils';
import { PlatformType } from '@/types';
import { getPlatformIconComponent, getPlatformLabel, getPlatformColor } from '@/utils/platformUtils';
import { useTranslation } from 'react-i18next';

interface VisitorHeaderProps {
  name: string;
  status: 'online' | 'away' | 'offline';
  avatar: string;
  platformType?: PlatformType;
  lastSeenText?: string;
  className?: string;
  /** Callback when avatar is clicked for upload */
  onAvatarClick?: () => void;
  /** Whether avatar upload is in progress */
  isUploading?: boolean;
}

/**
 * 访客头部信息组件
 */
const VisitorHeader: React.FC<VisitorHeaderProps> = ({
  name,
  status,
  avatar,
  platformType,
  lastSeenText,
  className = '',
  onAvatarClick,
  isUploading = false
}) => {
  const { t } = useTranslation();
  // Use same avatar fallback logic as conversations list
  const hasValidAvatarUrl = hasValidAvatar(avatar);
  const defaultAvatar = useMemo(
    () => (!hasValidAvatarUrl ? generateDefaultAvatar(name) : null),
    [hasValidAvatarUrl, name]
  );

  const handleImageError = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    // Hide broken image and reveal fallback
    e.currentTarget.style.display = 'none';
    const fallback = e.currentTarget.nextElementSibling as HTMLElement | null;
    if (fallback) fallback.style.display = 'flex';
  }, []);
  const getStatusText = (status: string) => {
    switch (status) {
      case 'online': return t('chat.status.online', '在线');
      default: return undefined;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'text-green-600 dark:text-green-400';
      case 'away': return 'text-yellow-600 dark:text-yellow-400';
      case 'offline': return 'text-gray-500 dark:text-gray-400';
      default: return 'text-gray-500 dark:text-gray-400';
    }
  };

  return (
    <div className={`flex items-center ${className}`}>
      <div 
        className={`relative mr-3 group ${onAvatarClick ? 'cursor-pointer' : ''}`}
        onClick={onAvatarClick}
        title={onAvatarClick ? t('chat.visitor.avatar.uploadTitle', '点击上传头像') : undefined}
        role={onAvatarClick ? 'button' : undefined}
        tabIndex={onAvatarClick ? 0 : undefined}
        onKeyDown={onAvatarClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onAvatarClick(); } } : undefined}
      >
        {hasValidAvatarUrl ? (
          <img
            src={avatar}
            alt={`${name} Avatar`}
            className={`w-12 h-12 rounded-md object-cover bg-gray-200 dark:bg-gray-700 ${onAvatarClick ? 'group-hover:opacity-75 transition-opacity' : ''}`}
            onError={handleImageError}
          />
        ) : null}
        <div
          className={`w-12 h-12 rounded-md flex items-center justify-center text-white font-bold text-base ${
            hasValidAvatarUrl ? 'hidden' : ''
          } ${defaultAvatar?.colorClass || 'bg-gradient-to-br from-gray-400 to-gray-500'} ${onAvatarClick ? 'group-hover:opacity-75 transition-opacity' : ''}`}
          style={{ display: hasValidAvatarUrl ? 'none' : 'flex' }}
          aria-hidden={hasValidAvatarUrl}
        >
          {defaultAvatar?.letter || '?'}
        </div>
        {/* Upload overlay on hover */}
        {onAvatarClick && !isUploading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 rounded-md opacity-0 group-hover:opacity-100 transition-opacity">
            <Camera className="w-5 h-5 text-white" />
          </div>
        )}
        {/* Loading overlay */}
        {isUploading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-md">
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>
      <div className="flex-grow">
        <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 leading-5 truncate" title={name}>
          {name}
          {(() => {
            const type = platformType ?? PlatformType.WEBSITE;
            const IconComp = getPlatformIconComponent(type);
            const label = getPlatformLabel(type);
            return (
              <span title={label}>
                <IconComp size={14} className={`w-3.5 h-3.5 inline-block ml-1 -mt-0.5 ${getPlatformColor(type)}`} />
              </span>
            );
          })()}
        </h3>
        <p className={`text-xs leading-4 mt-0.5 ${getStatusColor(status)}`}>
          {lastSeenText ?? getStatusText(status)}
        </p>
      </div>
    </div>
  );
};

export default VisitorHeader;
