'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { 
  Center, 
  Spinner, 
  useToast, 
  Box, 
  VStack, 
  Text, 
  Alert, 
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Progress,
  Container,
  Heading,
  Icon
} from '@chakra-ui/react'
import { FaCheckCircle, FaExclamationTriangle } from 'react-icons/fa'

export default function Callback() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const toast = useToast()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState<string>('Discordアカウントと連携中...')
  const [progress, setProgress] = useState<number>(10)

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // プログレスバーのアニメーション
        const interval = setInterval(() => {
          setProgress((prev) => {
            if (prev >= 90) {
              clearInterval(interval)
              return 90
            }
            return prev + 10
          })
        }, 300)

        const code = searchParams.get('code')
        if (!code) {
          setStatus('error')
          setMessage('認証コードが見つかりません')
          clearInterval(interval)
          throw new Error('認証コードが見つかりません')
        }

        setMessage('Discord認証情報を検証中...')

        // コードをバックエンドに送信
        const response = await fetch(`/api/auth/discord/callback?code=${code}`)
        const data = await response.json()

        if (!response.ok) {
          setStatus('error')
          setMessage(data.detail || 'ログインに失敗しました')
          clearInterval(interval)
          throw new Error(data.detail || 'ログインに失敗しました')
        }

        setMessage('認証に成功しました！リダイレクトします...')

        // トークンを保存
        localStorage.setItem('token', data.access_token)
        
        // ユーザー情報を保存
        localStorage.setItem('user', JSON.stringify(data.user))

        // プログレスバーを完了
        clearInterval(interval)
        setProgress(100)
        setStatus('success')

        toast({
          title: 'ログイン成功',
          description: 'Shard Bot管理パネルへようこそ！',
          status: 'success',
          duration: 3000,
          isClosable: true,
        })

        // 少し待ってからリダイレクト
        setTimeout(() => {
          // ダッシュボードにリダイレクト
          router.push('/dashboard')
        }, 1500)
      } catch (error) {
        console.error('認証エラー:', error)
        setStatus('error')
        
        toast({
          title: 'エラー',
          description: error instanceof Error ? error.message : 'ログインに失敗しました',
          status: 'error',
          duration: 5000,
          isClosable: true,
        })

        // エラー表示後、少し待ってからログインページに戻る
        setTimeout(() => {
          router.push('/auth/login')
        }, 3000)
      }
    }

    handleCallback()
  }, [router, searchParams, toast])

  return (
    <Box 
      minH="100vh" 
      bgGradient="linear(to-br, blue.400, purple.500)"
      display="flex"
      alignItems="center"
      justifyContent="center"
    >
      <Container maxW="md">
        <Box
          p={8}
          borderRadius="xl"
          boxShadow="xl"
          bg="white"
          _dark={{ bg: 'gray.800' }}
        >
          <VStack spacing={6}>
            {status === 'loading' && (
              <>
                <Spinner size="xl" thickness="4px" color="purple.500" speed="0.65s" />
                <Progress 
                  value={progress} 
                  size="sm" 
                  width="100%" 
                  colorScheme="purple" 
                  borderRadius="full"
                  hasStripe
                  isAnimated
                />
                <Text fontSize="lg" fontWeight="medium">{message}</Text>
              </>
            )}

            {status === 'success' && (
              <>
                <Icon as={FaCheckCircle} w={16} h={16} color="green.500" />
                <Heading size="md">認証成功</Heading>
                <Text>{message}</Text>
                <Progress 
                  value={100} 
                  size="sm" 
                  width="100%" 
                  colorScheme="green" 
                  borderRadius="full"
                />
              </>
            )}

            {status === 'error' && (
              <>
                <Icon as={FaExclamationTriangle} w={16} h={16} color="red.500" />
                <Heading size="md">認証エラー</Heading>
                <Alert status="error" borderRadius="md">
                  <AlertIcon />
                  <AlertDescription>{message}</AlertDescription>
                </Alert>
                <Text fontSize="sm">ログインページに戻ります...</Text>
              </>
            )}
          </VStack>
        </Box>
      </Container>
    </Box>
  )
} 