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
          throw new Error('認証トークンがありません')
        }

        // セッションの検証
        console.log('セッション検証リクエスト送信...')
        const response = await fetch('/api/auth/session', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })
        
        console.log('レスポンスステータス:', response.status)
        const responseText = await response.text()
        console.log('レスポンス本文:', responseText)

        let data
        try {
          data = JSON.parse(responseText)
          console.log('パース済みレスポンス:', data)
        } catch (e) {
          console.error('JSONパースエラー:', e)
          throw new Error('レスポンスの解析に失敗しました')
        }

        if (!response.ok) {
          console.error('セッション検証エラー:', data)
          throw new Error(data.detail || 'セッションが無効です')
        }

        if (data.status !== 'success' || !data.data?.user) {
          console.error('ユーザー情報が取得できません:', data)
          throw new Error('ユーザー情報が取得できません')
        }

        console.log('セッション検証成功:', data.data.user)
        console.log('=== セッション検証完了 ===')
        setIsLoading(false)
      } catch (error) {
        console.error('認証エラー詳細:', error)
        if (error instanceof Error) {
          console.error('エラーメッセージ:', error.message)
          console.error('エラースタック:', error.stack)
        }
        
        // エラーメッセージを表示
        toast({
          title: '認証エラー',
          description: error instanceof Error ? error.message : '認証に失敗しました',
          status: 'error',
          duration: 5000,
          isClosable: true,
        })

        // 3秒待ってからリダイレクト
        console.log('3秒後にログインページにリダイレクトします...')
        await new Promise(resolve => setTimeout(resolve, 3000))
        
        localStorage.removeItem('token')
        localStorage.removeItem('user')
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