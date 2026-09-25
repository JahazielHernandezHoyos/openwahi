'use client'

import { useState } from 'react'
import { useItems } from '@/modules/items/hooks/useItems'
import { ItemCreate } from '@/modules/items/types'
import { Header } from '@/components/layout/Header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Trash2, AlertCircle } from 'lucide-react'
import { useTranslations } from 'next-intl'

export default function ItemsPage() {
  const t = useTranslations('Items')
  const { items, loading, error, createItem, deleteItem } = useItems()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!title.trim()) {
      setFormError(t('errors.titleRequired'))
      return
    }

    try {
      setIsSubmitting(true)
      const newItem: ItemCreate = {
        title: title.trim(),
        description: description.trim() || undefined,
      }
      await createItem(newItem)
      setTitle('')
      setDescription('')
    } catch (error) {
      setFormError(t('errors.createError'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteItem(id)
    } catch (error) {
      // Error silenciado
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">{t('title')}</h1>

        {/* Formulario de creación */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>{t('createNew')}</CardTitle>
            <CardDescription>{t('addDesc')}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {formError && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="title">{t('titleLabel')}</Label>
                <Input
                  type="text"
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder={t('titlePlaceholder')}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">{t('descriptionLabel')}</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  placeholder={t('descriptionPlaceholder')}
                />
              </div>

              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? t('creating') : t('createButton')}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Lista de items */}
        <div>
          <h2 className="text-xl font-semibold mb-4">{t('myItems')}</h2>

          {loading && (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <Card key={i}>
                  <CardContent className="pt-6">
                    <Skeleton className="h-6 w-48 mb-2" />
                    <Skeleton className="h-4 w-full mb-3" />
                    <Skeleton className="h-3 w-32" />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {!loading && !error && items.length === 0 && (
            <Card>
              <CardContent className="pt-6 text-center">
                <p className="text-muted-foreground">{t('noItems')}</p>
                <p className="text-sm text-muted-foreground mt-2">
                  {t('createFirst')}
                </p>
              </CardContent>
            </Card>
          )}

          {!loading && items.length > 0 && (
            <div className="space-y-4">
              {items.map((item) => (
                <Card key={item.id}>
                  <CardContent className="pt-6">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold">{item.title}</h3>
                        {item.description && (
                          <p className="text-muted-foreground mt-2">{item.description}</p>
                        )}
                        <p className="text-xs text-muted-foreground mt-3">
                          {t('created')}: {new Date(item.created_at).toLocaleDateString()}
                        </p>
                      </div>

                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>{t('deleteTitle')}</AlertDialogTitle>
                            <AlertDialogDescription>
                              {t('deleteDesc', { title: item.title })}
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDelete(item.id)}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            >
                              {t('delete')}
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
