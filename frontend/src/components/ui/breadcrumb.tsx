// 面包屑导航 - 完全参照 kiro.rs
import Link from 'next/link'
import { ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BreadcrumbItem {
  label: string
  href?: string
  icon?: React.ReactNode
}

interface BreadcrumbProps {
  items: BreadcrumbItem[]
  className?: string
}

export function Breadcrumb({ items, className }: BreadcrumbProps) {
  return (
    <nav className={cn('flex items-center gap-2 text-[13px]', className)}>
      {items.map((item, index) => {
        const isLast = index === items.length - 1
        
        return (
          <div key={index} className="flex items-center gap-2">
            {item.icon && (
              <span className="text-primary">{item.icon}</span>
            )}
            
            {item.href && !isLast ? (
              <Link
                href={item.href}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {item.label}
              </Link>
            ) : (
              <span className={cn(
                isLast 
                  ? 'text-foreground font-medium' 
                  : 'text-muted-foreground'
              )}>
                {item.label}
              </span>
            )}
            
            {!isLast && (
              <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/50" />
            )}
          </div>
        )
      })}
    </nav>
  )
}
