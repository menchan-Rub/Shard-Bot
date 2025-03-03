'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
  Card,
  CardHeader,
  CardBody,
  Button,
  useToast,
} from '@chakra-ui/react'

export default function Dashboard() {
  const [user, setUser] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()
  const toast = useToast()

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('token')
        
        if (!token) {
          router.push('/auth/login')
          return
        }
        
        const response = await fetch('/api/auth/session', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        })
        
        if (!response.ok) {
          throw new Error('認証に失敗しました')
        }
        
        const data = await response.json()
        
        if (data.status === 'success' && data.data?.user) {
          setUser(data.data.user)
        } else {
          throw new Error('ユーザー情報の取得に失敗しました')
        }
      } catch (error) {
        console.error('認証エラー:', error)
        localStorage.removeItem('token')
        toast({
          title: '認証エラー',
          description: '再度ログインしてください',
          status: 'error',
          duration: 3000,
          isClosable: true,
        })
        router.push('/auth/login')
      } finally {
        setIsLoading(false)
      }
    }
    
    checkAuth()
  }, [router, toast])
  
  if (isLoading) {
    return (
      <Container maxW="container.xl" py={10}>
        <Text>読み込み中...</Text>
      </Container>
    )
  }
  
  return (
    <Container maxW="container.xl" py={10}>
      <VStack spacing={8} align="stretch">
        <HStack justify="space-between">
          <Box>
            <Heading size="lg">ダッシュボード</Heading>
            <Text>ようこそ、{user?.username || 'ユーザー'}さん</Text>
          </Box>
          <Button
            onClick={() => {
              localStorage.removeItem('token')
              router.push('/auth/login')
            }}
          >
            ログアウト
          </Button>
        </HStack>
        
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
          <Card>
            <CardHeader>
              <Heading size="md">サーバー数</Heading>
            </CardHeader>
            <CardBody>
              <Stat>
                <StatNumber>0</StatNumber>
                <StatHelpText>接続済みサーバー</StatHelpText>
              </Stat>
            </CardBody>
          </Card>
          
          <Card>
            <CardHeader>
              <Heading size="md">ユーザー数</Heading>
            </CardHeader>
            <CardBody>
              <Stat>
                <StatNumber>0</StatNumber>
                <StatHelpText>総ユーザー数</StatHelpText>
              </Stat>
            </CardBody>
          </Card>
          
          <Card>
            <CardHeader>
              <Heading size="md">コマンド実行数</Heading>
            </CardHeader>
            <CardBody>
              <Stat>
                <StatNumber>0</StatNumber>
                <StatHelpText>過去24時間</StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>
        
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
          <Card>
            <CardHeader>
              <Heading size="md">最近のアクティビティ</Heading>
            </CardHeader>
            <CardBody>
              <Text>データがありません</Text>
            </CardBody>
          </Card>
          
          <Card>
            <CardHeader>
              <Heading size="md">システム状態</Heading>
            </CardHeader>
            <CardBody>
              <VStack align="stretch">
                <HStack justify="space-between">
                  <Text>API サーバー</Text>
                  <Text color="green.500">オンライン</Text>
                </HStack>
                <HStack justify="space-between">
                  <Text>Bot</Text>
                  <Text color="green.500">オンライン</Text>
                </HStack>
                <HStack justify="space-between">
                  <Text>データベース</Text>
                  <Text color="green.500">オンライン</Text>
                </HStack>
              </VStack>
            </CardBody>
          </Card>
        </SimpleGrid>
      </VStack>
    </Container>
  )
} 