'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Center, Spinner, useToast } from '@chakra-ui/react'

export default function Callback() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const toast = useToast()

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = searchParams.get('code')
        if (!code) {
          throw new Error('認証コードが見つかりません')
        }

        // コードをバックエンドに送信
        const response = await fetch(`/api/auth/discord/callback?code=${code}`)
        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail || 'ログインに失敗しました')
        }

        // トークンを保存
        localStorage.setItem('token', data.access_token)
        
        // ユーザー情報を保存
        localStorage.setItem('user', JSON.stringify(data.user))

        toast({
          title: 'ログイン成功',
          status: 'success',
          duration: 3000,
          isClosable: true,
        })

        // ダッシュボードにリダイレクト
        router.push('/dashboard')
      } catch (error) {
        console.error('認証エラー:', error)
        toast({
          title: 'エラー',
          description: error instanceof Error ? error.message : 'ログインに失敗しました',
          status: 'error',
          duration: 5000,
          isClosable: true,
        })
        router.push('/auth/login')
      }
    }

    handleCallback()
  }, [router, searchParams, toast])

  return (
    <Center minH="100vh">
      <Spinner size="xl" />
    </Center>
  )
} 