'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Box, Spinner, Center } from '@chakra-ui/react'

export default function HomePage() {
  const router = useRouter()

  useEffect(() => {
    // ログインページにリダイレクト
    router.push('/auth/login')
  }, [router])

  return (
    <Center h="100vh">
      <Box>
        <Spinner size="xl" />
      </Box>
    </Center>
  )
}
