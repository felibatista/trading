import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatUsd, pnlColor } from '@/lib/format'
import type { Position } from '@/lib/types'

export function PositionsTable({ positions }: { positions: Position[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold text-zinc-900">Posiciones abiertas</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Símbolo</TableHead>
              <TableHead>Lado</TableHead>
              <TableHead className="text-right">Entrada</TableHead>
              <TableHead className="text-right">Actual</TableHead>
              <TableHead className="text-right">P&L</TableHead>
              <TableHead className="text-right">Stop</TableHead>
              <TableHead className="text-right">Take</TableHead>
              <TableHead className="text-right">Valor</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {positions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-sm text-zinc-400">
                  Sin posiciones abiertas.
                </TableCell>
              </TableRow>
            ) : (
              positions.map((p) => {
                const current = p.entry_price // fallback: sin precio en vivo
                const pnl = (current - p.entry_price) * p.quantity
                const value = current * p.quantity
                return (
                  <TableRow key={p.symbol}>
                    <TableCell className="font-medium">{p.symbol}</TableCell>
                    <TableCell>Largo</TableCell>
                    <TableCell className="text-right tabular-nums">{formatUsd(p.entry_price)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatUsd(current)}</TableCell>
                    <TableCell className={`text-right tabular-nums ${pnlColor(pnl)}`}>{formatUsd(pnl)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatUsd(p.stop_loss)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatUsd(p.take_profit)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatUsd(value)}</TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
