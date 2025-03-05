'use client'

import { useEffect, useState } from 'react'
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
  const toast = useToast()

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) return
        
        const response = await fetch('/api/auth/session', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          },
        })
        
        const data = await response.json()
        
        if (data.status === 'success' && data.data?.user) {
          setUser(data.data.user)
        }
      } catch (error) {
        console.error('ユーザー情報の取得に失敗:', error)
        toast({
          title: 'エラー',
          description: 'ユーザー情報の取得に失敗しました',
          status: 'error',
          duration: 3000,
          isClosable: true,
        })
      } finally {
        setIsLoading(false)
      }
    }
    
    fetchUserData()
  }, [toast])
  
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
        <Heading size="lg">ダッシュボード</Heading>
        {user && (
          <Text>ようこそ、{user.username}さん</Text>
        )}
        
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
          <Card>
            <CardHeader>
              <Heading size="md">統計情報</Heading>
            </CardHeader>
            <CardBody>
              <VStack spacing={4}>
                <Stat>
                  <StatLabel>総サーバー数</StatLabel>
                  <StatNumber>10</StatNumber>
                  <StatHelpText>過去30日間</StatHelpText>
                </Stat>
              </VStack>
            </CardBody>
          </Card>
          
          {/* 他の統計情報カードをここに追加 */}
        </SimpleGrid>
      </VStack>
    </Container>
  )
} 