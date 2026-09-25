import en from '../../messages/en.json';
import es from '../../messages/es.json';

const dictionaries: any = { en, es };

export type Locale = 'en' | 'es';

export const getDictionary = (locale: Locale) => {
    return dictionaries[locale] || dictionaries.es;
};

export const getLocaleFromServer = (cookies: any) => {
    return cookies.get('NEXT_LOCALE')?.value || 'es';
};
