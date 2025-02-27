'use client'

import { Box, Flex } from '@chakra-ui/react'
import Sidebar from '../components/Sidebar'
import Header from '../components/Header'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
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