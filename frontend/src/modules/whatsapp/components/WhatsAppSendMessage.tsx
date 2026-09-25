'use client'

import { useState } from 'react'
import { useWhatsAppMessages } from '../hooks/useWhatsAppMessages'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { FormContainer } from '@/components/shared/FormContainer'
import { Send, CheckCircle2, AlertCircle } from 'lucide-react'
import { useTranslations } from 'next-intl'

interface WhatsAppSendMessageProps {
  deviceId: string | null
  isConnected: boolean
}

export function WhatsAppSendMessage({ deviceId, isConnected }: WhatsAppSendMessageProps) {
  const t = useTranslations('WhatsApp.sendMessage')
  const { sendMessage, isSending, sendError } = useWhatsAppMessages(deviceId)
  const [phone, setPhone] = useState('')
  const [message, setMessage] = useState('')
  const [success, setSuccess] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError(null)
    setSuccess(false)

    if (!phone.trim()) {
      setLocalError(t('phoneRequired'))
      return
    }

    const normalizedPhone = phone.replace(/\D/g, '')
    if (!/^\d{8,15}$/.test(normalizedPhone)) {
      setLocalError(t('phoneInvalid'))
      return
    }

    if (!message.trim()) {
      setLocalError(t('messageRequired'))
      return
    }

    if (!deviceId) {
      setLocalError(t('selectDevice'))
      return
    }

    try {
      const result = await sendMessage({
        phone: normalizedPhone,
        message: message.trim(),
      })

      if (result.success) {
        setSuccess(true)
        setMessage('')
        setTimeout(() => setSuccess(false), 3000)
      } else {
        setLocalError(result.error || t('error'))
      }
    } catch (err) {
      setLocalError(t('error'))
    }
  }

  const error = localError || sendError

  return (
    <FormContainer
      title={t("title")}
      description={t("description")}
      icon={Send}
    >
      <div className="space-y-6">
        {!isConnected && (
          <Alert variant="destructive" className="border-none bg-destructive/10">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="font-medium">
              {t("notConnected")}
            </AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert variant="success">
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription className="font-medium">{t("success")}</AlertDescription>
            </Alert>
          )}

          <div className="grid gap-6">
            <div className="space-y-2">
              <Label htmlFor="phone" className="text-sm font-semibold tracking-tight">
                {t("phoneLabel")}
              </Label>
              <Input
                id="phone"
                type="tel"
                placeholder={t("phonePlaceholder")}
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                disabled={!isConnected || isSending}
                className="bg-muted/30 border-muted-foreground/10 focus:bg-background transition-all"
              />
              <p className="text-[11px] text-muted-foreground leading-normal">
                {t("phoneHelp")}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="message" className="text-sm font-semibold tracking-tight">
                {t("messageLabel")}
              </Label>
              <Textarea
                id="message"
                placeholder={t("messagePlaceholder")}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={4}
                disabled={!isConnected || isSending}
                className="bg-muted/30 border-muted-foreground/10 focus:bg-background transition-all resize-none"
              />
            </div>
          </div>

          <Button
            type="submit"
            disabled={!isConnected || isSending || !deviceId}
            className="w-full h-11 text-sm font-bold shadow-lg shadow-primary/20 hover:shadow-primary/30 active:scale-[0.98] transition-all"
          >
            {isSending ? (
              <div className="flex items-center gap-2">
                <span className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                {t("sending")}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Send className="h-4 w-4" />
                {t("send")}
              </div>
            )}
          </Button>
        </form>
      </div>
    </FormContainer>
  )
}
