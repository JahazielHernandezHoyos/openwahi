'use client'

import { useAuth } from '@/context/AuthContext'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, Link } from '@/i18n/routing'
import { useTranslations } from 'next-intl'
import { useLocale } from 'next-intl'
import { useMounted } from '@/tools/hooks/useMounted'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { MessageSquare, Bot, Zap, Smartphone, Globe, AlertCircle } from 'lucide-react'
import { useSearchParams } from 'next/navigation'
import { APP_NAME } from '@/config/brand'

// Component to handle error messages from URL params
function ErrorAlert() {
  const searchParams = useSearchParams()
  const locale = useLocale()
  const mounted = useMounted()
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!mounted) return;

    const error = searchParams.get('error');
    const email = searchParams.get('email');

    if (error === 'email_not_allowed') {
      const message = locale === 'es'
        ? `El correo ${email || ''} no tiene permisos para acceder a la plataforma. Contacta al administrador.`
        : `The email ${email || ''} is not authorized to access the platform. Contact the administrator.`;
      setErrorMessage(message);
    } else if (error === 'auth_callback_error') {
      const message = locale === 'es'
        ? 'Error al iniciar sesión. Por favor intenta de nuevo.'
        : 'Error signing in. Please try again.';
      setErrorMessage(message);
    }
  }, [mounted, searchParams, locale])

  if (!errorMessage) return null;

  return (
    <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3 animate-slide-up">
      <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
      <p className="text-sm text-red-800 dark:text-red-200">{errorMessage}</p>
    </div>
  );
}

function LoginPageContent() {
  const t = useTranslations('Auth')
  const { signInWithGoogle, user, loading } = useAuth()
  const router = useRouter()
  const mounted = useMounted()
  const locale = useLocale()
  const otherLocale = locale === 'es' ? 'en' : 'es'

  useEffect(() => {
    if (mounted && user && !loading) {
      router.push('/dashboard')
    }
  }, [mounted, user, loading, router])

  const handleGoogleLogin = async () => {
    try {
      await signInWithGoogle()
    } catch (error) {
      // Error silenciado
    }
  }

  const showLoading = !mounted || loading

  if (showLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-sky-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800" suppressHydrationWarning>
        <Card className="w-full max-w-md animate-pulse">
          <CardHeader className="text-center">
            <Skeleton className="h-8 w-48 mx-auto" />
            <Skeleton className="h-4 w-64 mx-auto mt-2" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-11 w-full" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex" suppressHydrationWarning>
      {/* Custom Animations */}
      <style jsx global>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-20px) rotate(5deg); }
        }
        @keyframes float-reverse {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(20px) rotate(-5deg); }
        }
        @keyframes float-slow {
          0%, 100% { transform: translateY(0px) scale(1); }
          50% { transform: translateY(-30px) scale(1.05); }
        }
        @keyframes slide-up {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slide-right {
          from { opacity: 0; transform: translateX(-20px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes bounce-subtle {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-5px); }
        }
        .animate-float { animation: float 6s ease-in-out infinite; }
        .animate-float-reverse { animation: float-reverse 7s ease-in-out infinite; }
        .animate-float-slow { animation: float-slow 8s ease-in-out infinite; }
        .animate-slide-up { animation: slide-up 0.6s ease-out forwards; }
        .animate-slide-right { animation: slide-right 0.6s ease-out forwards; }
        .animate-fade-in { animation: fade-in 0.8s ease-out forwards; }
        .animate-bounce-subtle { animation: bounce-subtle 2s ease-in-out infinite; }
        .animation-delay-100 { animation-delay: 100ms; }
        .animation-delay-200 { animation-delay: 200ms; }
        .animation-delay-300 { animation-delay: 300ms; }
        .animation-delay-400 { animation-delay: 400ms; }
        .animation-delay-500 { animation-delay: 500ms; }
        .animation-delay-700 { animation-delay: 700ms; }
        .animation-delay-1000 { animation-delay: 1000ms; }
      `}</style>

      {/* Language Switcher */}
      <div className="absolute top-4 right-4 z-10 animate-fade-in animation-delay-500">
        <Link href="/login" locale={otherLocale}>
          <Button
            variant="outline"
            size="sm"
            className="gap-2 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm hover:scale-105 transition-all duration-300 hover:shadow-lg"
          >
            <Globe className="h-4 w-4 animate-spin" style={{ animationDuration: '10s' }} />
            {t('switchLanguage')}
          </Button>
        </Link>
      </div>

      {/* Left Panel - Branding & Features */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-800 via-blue-600 to-sky-500 p-12 flex-col justify-between relative overflow-hidden">
        {/* Animated Background Circles */}
        <div className="absolute inset-0">
          <div className="absolute top-10 left-10 w-20 h-20 border-4 border-white rounded-full animate-float opacity-20" />
          <div className="absolute top-40 right-20 w-32 h-32 border-4 border-white rounded-full animate-float-reverse opacity-15" style={{ animationDelay: '1s' }} />
          <div className="absolute bottom-20 left-1/4 w-24 h-24 border-4 border-white rounded-full animate-float-slow opacity-20" style={{ animationDelay: '2s' }} />
          <div className="absolute bottom-40 right-10 w-16 h-16 border-4 border-white rounded-full animate-float opacity-25" style={{ animationDelay: '0.5s' }} />
          <div className="absolute top-1/2 left-10 w-12 h-12 border-4 border-white rounded-full animate-float-reverse opacity-15" style={{ animationDelay: '1.5s' }} />
          <div className="absolute top-20 right-1/3 w-8 h-8 border-4 border-white rounded-full animate-float-slow opacity-20" style={{ animationDelay: '3s' }} />
        </div>

        {/* Logo & Title */}
        <div className="relative z-10 animate-slide-right">
          <div className="flex items-center gap-3 mb-6 group">
            <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300 group-hover:rotate-6">
              <MessageSquare className="w-7 h-7 text-slate-600" />
            </div>
            <span className="text-2xl font-bold text-white">{APP_NAME}</span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-4 animate-slide-up animation-delay-200">
            {t('signInTitle')}
          </h1>
          <p className="text-lg text-sky-100 max-w-md animate-slide-up animation-delay-300 opacity-0" style={{ animationFillMode: 'forwards' }}>
            {t('signInSubtitle')}
          </p>
        </div>

        {/* Features with staggered animations */}
        <div className="relative z-10 space-y-6">
          <div className="flex items-start gap-4 animate-slide-right opacity-0 animation-delay-400" style={{ animationFillMode: 'forwards' }}>
            <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0 hover:bg-white/30 hover:scale-110 transition-all duration-300 group cursor-pointer">
              <Smartphone className="w-6 h-6 text-white group-hover:animate-bounce-subtle" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{t('feature1Title')}</h3>
              <p className="text-sky-100">{t('feature1Desc')}</p>
            </div>
          </div>

          <div className="flex items-start gap-4 animate-slide-right opacity-0 animation-delay-500" style={{ animationFillMode: 'forwards' }}>
            <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0 hover:bg-white/30 hover:scale-110 transition-all duration-300 group cursor-pointer">
              <Bot className="w-6 h-6 text-white group-hover:animate-bounce-subtle" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{t('feature2Title')}</h3>
              <p className="text-sky-100">{t('feature2Desc')}</p>
            </div>
          </div>

          <div className="flex items-start gap-4 animate-slide-right opacity-0 animation-delay-700" style={{ animationFillMode: 'forwards' }}>
            <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0 hover:bg-white/30 hover:scale-110 transition-all duration-300 group cursor-pointer">
              <Zap className="w-6 h-6 text-white group-hover:animate-bounce-subtle" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{t('feature3Title')}</h3>
              <p className="text-sky-100">{t('feature3Desc')}</p>
            </div>
          </div>
        </div>

        {/* Decorative Element */}
        <div className="relative z-10 animate-fade-in animation-delay-1000">
          <div className="flex items-center gap-2 text-sky-100 text-sm">
            <div className="w-2 h-2 bg-sky-300 rounded-full animate-pulse" />
            <span>Secure & Encrypted</span>
          </div>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-gradient-to-br from-slate-50 via-blue-50 to-sky-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800 relative overflow-hidden">
        <div className="w-full max-w-md relative z-10">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8 animate-slide-up">
            <div className="w-10 h-10 bg-slate-600 rounded-xl flex items-center justify-center shadow-lg hover:scale-110 transition-transform duration-300">
              <MessageSquare className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900 dark:text-white">{APP_NAME}</span>
          </div>

          <Card className="border-0 shadow-xl bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm animate-slide-up hover:shadow-2xl transition-shadow duration-500">
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-2xl font-bold text-gray-900 dark:text-white animate-fade-in animation-delay-200">
                {t('welcome')}
              </CardTitle>
              <CardDescription className="text-gray-600 dark:text-gray-400 animate-fade-in animation-delay-300">
                {t('signInSubtitle')}
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              {/* Error Alert */}
              <Suspense fallback={null}>
                <ErrorAlert />
              </Suspense>

              <Button
                variant="outline"
                className="w-full h-12 text-base font-medium border-2 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-300 hover:scale-[1.02] hover:shadow-lg active:scale-[0.98] animate-slide-up animation-delay-400 group"
                onClick={handleGoogleLogin}
              >
                <svg className="w-5 h-5 mr-3 group-hover:animate-bounce-subtle" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                {t('continueWithGoogle')}
              </Button>

              {/* Mobile Features */}
              <div className="lg:hidden mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="flex flex-col items-center animate-slide-up animation-delay-500 group cursor-pointer">
                    <div className="w-10 h-10 bg-slate-100 dark:bg-slate-900/30 rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 group-hover:bg-slate-200 dark:group-hover:bg-slate-800/40 transition-all duration-300">
                      <Smartphone className="w-5 h-5 text-slate-600 dark:text-slate-400 group-hover:animate-bounce-subtle" />
                    </div>
                    <span className="text-xs text-gray-600 dark:text-gray-400">{t('feature1Title')}</span>
                  </div>
                  <div className="flex flex-col items-center animate-slide-up animation-delay-700 group cursor-pointer">
                    <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 group-hover:bg-blue-200 dark:group-hover:bg-blue-800/40 transition-all duration-300">
                      <Bot className="w-5 h-5 text-blue-500 dark:text-blue-400 group-hover:animate-bounce-subtle" />
                    </div>
                    <span className="text-xs text-gray-600 dark:text-gray-400">{t('feature2Title')}</span>
                  </div>
                  <div className="flex flex-col items-center animate-slide-up animation-delay-1000 group cursor-pointer">
                    <div className="w-10 h-10 bg-sky-100 dark:bg-sky-900/30 rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 group-hover:bg-sky-200 dark:group-hover:bg-sky-800/40 transition-all duration-300">
                      <Zap className="w-5 h-5 text-sky-500 dark:text-sky-400 group-hover:animate-bounce-subtle" />
                    </div>
                    <span className="text-xs text-gray-600 dark:text-gray-400">{t('feature3Title')}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
      <LoginPageContent />
    </Suspense>
  )
}
