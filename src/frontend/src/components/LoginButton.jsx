import React from 'react';

const LoginButton = ({ userInfo, onToggleHistory, onToggleLogin, onToggleRegister, onLogout }) => {
    if (userInfo) {
        return (
            <div className="flex items-center gap-4">

                <span className="text-sm font-medium text-gray-700 dark:text-gray-200 border-l border-gray-300 dark:border-gray-600 pl-4">
                    {userInfo.userDetails}
                </span>
                <button
                    onClick={onLogout}
                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                    Logout
                </button>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2">
            <button
                onClick={onToggleLogin}
                className="px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
            >
                Log In
            </button>
            <button
                onClick={onToggleRegister}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
                Sign Up
            </button>
        </div>
    );
};

export default LoginButton;
