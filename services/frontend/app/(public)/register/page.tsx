import { Metadata } from 'next';
import Link from 'next/link';
import { RegistrationForm } from '@/components/features/auth/RegistrationForm';

export const metadata: Metadata = {
  title: 'Create Account | LICS',
  description: 'Create your LICS account',
};

export default function RegisterPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Logo and header */}
        <div className="text-center">
          <Link href="/" className="inline-block">
            <h1 className="text-4xl font-bold text-blue-600">LICS</h1>
          </Link>
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Start managing your laboratory instruments
          </p>
        </div>

        {/* Registration form */}
        <div className="mt-8 bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <RegistrationForm />
        </div>
      </div>
    </div>
  );
}
