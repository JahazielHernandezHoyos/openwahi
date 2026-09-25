'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

type Translations = any;

interface LanguageContextType {
    locale: string;
    t: (path: string) => string;
    setLocale: (locale: string) => void;
    isLoading: boolean;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider = ({
    children,
    initialLocale,
    initialMessages
}: {
    children: React.ReactNode,
    initialLocale: string,
    initialMessages: Translations
}) => {
    const [locale, setLocaleState] = useState(initialLocale);
    const [messages, setMessages] = useState(initialMessages);
    const [isLoading, setIsLoading] = useState(false);

    const setLocale = async (newLocale: string) => {
        setIsLoading(true);
        // Update cookie
        document.cookie = `NEXT_LOCALE=${newLocale}; path=/; max-age=31536000`;

        // In a more complex app, we'd fetch the JSON here
        // For this simple version, we'll just reload or use the imported ones if pre-loaded
        window.location.reload();
    };

    const t = (path: string) => {
        const keys = path.split('.');
        let value = messages;
        for (const key of keys) {
            value = value?.[key];
        }
        return typeof value === 'string' ? value : path;
    };

    return (
        <LanguageContext.Provider value={{ locale, t, setLocale, isLoading }}>
            {children}
        </LanguageContext.Provider>
    );
};

export const useTranslation = () => {
    const context = useContext(LanguageContext);
    if (context === undefined) {
        throw new Error('useTranslation must be used within a LanguageProvider');
    }
    return context;
};
