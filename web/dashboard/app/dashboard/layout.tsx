'use client'

import { useEffect, useState } from 'react'
import { Box, Flex, Spinner, Center, useToast } from '@chakra-ui/react'
import { useRouter } from 'next/navigation'
import Sidebar from '../components/Sidebar'
import Header from '../components/Header'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const toast = useToast()

  useEffect(() => {
    const checkAuth = async () => {
      try {
        console.log('=== セッション検証開始 ===')
        const token = localStorage.getItem('token')
        console.log('保存されているトークン:', token ? `${token.substring(0, 20)}...` : 'なし')
        
        if (!token) {
          console.error('認証トークンがありません')
          toast({
            title: '認証エラー',
            description: 'ログインが必要です',
            status: 'error',
            duration: 5000,
            isClosable: true,
          })
          router.push('/auth/login')
          return
        }

        // セッションの検証
        console.log('セッション検証リクエスト送信...')
        const response = await fetch('/api/auth/session', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          },
        })
        
        console.log('レスポンスステータス:', response.status)
        
        if (!response.ok) {
          throw new Error('セッションが無効です')
        }

        const data = await response.json()
        console.log('パース済みレスポンス:', data)

        if (data.status !== 'success' || !data.data?.user) {
          throw new Error('セッション検証に失敗しました')
        }

        console.log('セッション検証成功:', data.data?.user)
        console.log('=== セッション検証完了 ===')
        setIsLoading(false)
      } catch (error) {
        console.error('認証エラー詳細:', error)
        
        // トークンを削除
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        
        // エラーメッセージを表示
        toast({
          title: '認証エラー',
          description: error instanceof Error ? error.message : '認証に失敗しました。再度ログインしてください。',
          status: 'error',
          duration: 5000,
          isClosable: true,
        })
        
        router.push('/auth/login')
      }
    }

    checkAuth()
  }, [router, toast])

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    )
  }

  return (
    <Flex h="100vh">
      <Sidebar />
      <Box flex="1">
        <Header />
        <Box p={8}>
          {children}
        </Box>
      </Box>
    </Flex>
  )
} 