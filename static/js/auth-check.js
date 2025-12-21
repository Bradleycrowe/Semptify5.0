/**
 * Semptify Auth Check - Shared authentication verification
 * Works with storage middleware and handles graceful fallbacks
 */

const SemptifyAuth = {
    currentUser: null,
    
    /**
     * Get cookie value by name
     */
    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    },
    
    /**
     * Parse user ID to extract provider, role, and unique part
     */
    parseUserId(userId) {
        if (!userId || userId.length < 10) return null;
        
        const providerMap = {
            'G': { id: 'google', name: 'Google Drive', icon: '🔵' },
            'D': { id: 'dropbox', name: 'Dropbox', icon: '📦' },
            'O': { id: 'onedrive', name: 'OneDrive', icon: '☁️' }
        };
        
        const roleMap = {
            'U': { id: 'user', name: 'User', icon: '👤' },
            'M': { id: 'manager', name: 'Manager', icon: '👔' },
            'V': { id: 'advocate', name: 'Advocate', icon: '⚖️' },
            'L': { id: 'legal', name: 'Legal', icon: '📜' },
            'A': { id: 'admin', name: 'Admin', icon: '🔑' }
        };
        
        const providerCode = userId.charAt(0);
        const roleCode = userId.charAt(1);
        
        const provider = providerMap[providerCode];
        const role = roleMap[roleCode];
        
        if (!provider || !role) return null;
        
        return {
            provider: provider.id,
            providerName: provider.name,
            providerIcon: provider.icon,
            role: role.id,
            roleName: role.name,
            roleIcon: role.icon,
            uniquePart: userId.substring(2)
        };
    },
    
    /**
     * Main auth check - verifies user is authenticated
     * Returns true if authenticated, false and redirects if not
     */
    async check(options = {}) {
        const {
            redirectUrl = '/storage/providers',
            updateUI = true,
            userIconId = 'userIcon',
            userRoleId = 'userRole',
            userIdElId = 'userId'
        } = options;
        
        const semptifyUid = this.getCookie('semptify_uid');
        
        // If no cookie, try to verify via API
        if (!semptifyUid) {
            try {
                const resp = await fetch('/api/storage/status', { credentials: 'include' });
                if (resp.ok) {
                    const data = await resp.json();
                    if (data.connected && data.user_id) {
                        this.currentUser = {
                            id: data.user_id,
                            provider: data.provider || 'storage',
                            providerName: data.provider_name || 'Cloud Storage',
                            providerIcon: '☁️',
                            role: 'user',
                            roleName: 'User',
                            roleIcon: '👤',
                            uniquePart: data.user_id.substring(2)
                        };
                        if (updateUI) this.updateUI(userIconId, userRoleId, userIdElId);
                        return true;
                    }
                }
            } catch (e) {
                console.log('Storage status check failed');
            }
            
            // No valid auth - redirect
            window.location.href = redirectUrl;
            return false;
        }
        
        // Parse the user ID
        const parsed = this.parseUserId(semptifyUid);
        if (!parsed) {
            // Invalid cookie - clear and redirect
            document.cookie = 'semptify_uid=; path=/; max-age=0';
            window.location.href = redirectUrl;
            return false;
        }
        
        this.currentUser = {
            id: semptifyUid,
            ...parsed
        };
        
        if (updateUI) this.updateUI(userIconId, userRoleId, userIdElId);
        return true;
    },
    
    /**
     * Update UI elements with user info
     */
    updateUI(userIconId, userRoleId, userIdElId) {
        if (!this.currentUser) return;
        
        const userIcon = document.getElementById(userIconId);
        const userRole = document.getElementById(userRoleId);
        const userId = document.getElementById(userIdElId);
        
        if (userIcon) userIcon.textContent = this.currentUser.roleIcon || '👤';
        if (userRole) userRole.textContent = this.currentUser.roleName || 'User';
        if (userId) userId.textContent = this.currentUser.id || '';
    },
    
    /**
     * Get current user (must call check() first)
     */
    getUser() {
        return this.currentUser;
    },
    
    /**
     * Quick check if user seems authenticated (doesn't verify with server)
     */
    hasAuthCookie() {
        return !!this.getCookie('semptify_uid');
    }
};

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SemptifyAuth;
}
