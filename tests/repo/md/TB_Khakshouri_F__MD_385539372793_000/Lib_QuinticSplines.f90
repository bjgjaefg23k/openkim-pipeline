
    module Lib_QuinticSpline
!---^^^^^^^^^^^^^^^^^^^^^^^^
!*      A quintic spline is an extension of the more familiar cubic spline,
!*      but with continuous derivatives up to fourth order ( cf cubic to 2nd ).
!*      The mathematics of the construction is very similar to that of the cubic spline
!*      ( see numerical recipes section 3.3 )
!*      Write the fourth derivative as continuous linear variation
!*          y"" = A v_i + B v_i+1
!*      with A = (x_i+1 - x)/(x_i+1-x_i) and B = 1-A
!*      then integrate.
!*      We expect to be given {x_i} and {y_i} as input, so set constants with
!*      condition y(x_i) = y_i and y"(x_i) = u_i
!*      giving
!*
!*          y = A y_i + B y_i+1
!*            + C u_i + D u_i+1
!*            + E v_i + F v_i+1
!*      with
!*          C = A/6 ( A^2 - 1 ) ( x_i+1 - x_i )^2
!*          D = B/6 ( B^2 - 1 ) ( x_i+1 - x_i )^2
!*          E = A/360 ( 3A^4 - 10A^2 + 7 ) ( x_i+1 - x_i )^4
!*          F = B/360 ( 3B^4 - 10B^2 + 7 ) ( x_i+1 - x_i )^4
!*
!*
!*      Complete by solving for {u_i} and {v_i} by insisting y',y",y'",y"" continuous.
!*
!*      It is more expensive to compute than cubic, as the matrix equation that you end
!*      up with is band diagonal, rather than tridiagonal.
!*
!*
!*
!*
!*      Author      :   Daniel Mason
!*      Version     :   1.0
!*      Revision    :   Feb 2012
!*
!*      note        :   must be compiled against LAPACK
!*      note        :   should be compiled with -r8 for double precision.

        implicit none
        private

        external    ::      DGESV

    !---

        public      ::      quinticSpline_ctor
        public      ::      report
        public      ::      delete

        public      ::      refit
        public      ::      splint
        public      ::      qsplint

    !---

        type,public     ::      quinticSpline
            private
            integer                     ::          N       !   number of knots
            real(kind=8),dimension(:),pointer   ::          x       !   x(1:N) position of knots
            real(kind=8),dimension(:),pointer   ::          y       !   y(1:N) value at knots
            real(kind=8),dimension(:),pointer   ::          u       !   y"(1:N) value at knots
            real(kind=8),dimension(:),pointer   ::          v       !   y""(1:N) value at knots
        end type quinticSpline

    !---

        interface   quinticSpline_ctor
            module procedure    quinticSpline_ctor0
        end interface

        interface   report
            module procedure    report0
        end interface

        interface delete
            module procedure    delete0
        end interface

    contains
!---^^^^^^^^

        function quinticSpline_ctor0( x,y ) result( this )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      quintic spline memory allocation and fitting
            real(kind=8),dimension(:),target,intent(in)     ::      x
            real(kind=8),dimension(:),target,intent(in)     ::      y
            type(quinticSpline)                     ::      this
            this%N = size(x)
            if (size(y) < size(x)) then
                write (unit=0,fmt='(a,2i12)') "size(y) , size(x)",size(y),size(x)
                stop "Lib_QuinticSpline::quinticSpline_ctor0 - error size(y) < size(x)"
            end if
            allocate( this%u(this%N) )
            allocate( this%v(this%N) )
            this%x => x
            this%y => y
            call refit(this)
            return
        end function quinticSpline_ctor0

        subroutine refit( this )
    !---^^^^^^^^^^^^^^^^^^^^^^^^
    !*      perform quintic spline fitting.
    !*      currently do it the slow way with full LAPACK linear equation solver
    !*              ie  solve A.B = C
    !*      this could be improved dramatically with some thought.
    !*
    !*      B order (u1,v1,u2,v2...uN,vN)
            type(quinticSpline),intent(inout)       ::      this

            real(kind=8),dimension(2*this%N,2*this%N)       ::      A
            real(kind=8),dimension(2*this%N)                ::      B
            integer,dimension(2*this%N)             ::      IPIV
            integer                                 ::      NRHS,LDA,LDB,INFO

            integer             ::      ii
            real(kind=8)                ::      dx1,dx2,idx1,idx2,dy1,dy2

        !---    sanity check: arrays allocated?
            if (this%N == 0) then
                write (unit=0,fmt='(a)') "Lib_QuinticSpline::refit - warning refitting unallocated spline?"
                return
            end if

        !---    sanity check: x in ascending order
            do ii = 1,this%N-1
                if ( this%x(ii) > this%x(ii+1) ) then
                    write (unit=0,fmt='(a,i6,2g16.8)') "ii,x(ii),x(ii+1)=",ii,this%x(ii),this%x(ii+1)
                    stop "Lib_QuinticSpline::refit - error x(:) array not in strict ascending order"
                end if
            end do

            NRHS = 1
            LDA = 2*this%N
            LDB = 2*this%N

            A = 0.0
            B = 0.0
            dx2 = this%x(2) - this%x(1)
            A(1,2)                  = 1
            A(2,1:4)                = (/ -6.0d0,0.0d0,6.0d0,-dx2*dx2 /)
            do ii = 2,this%N-1
                dx1 = this%x(ii) - this%x(ii-1)
                dx2 = this%x(ii+1) - this%x(ii)
                idx1 = 1.0/dx1      !   note: have already checked dx1>0
                idx2 = 1.0/dx2

                A( 2*ii-1, 2*ii-3:2*ii+2 ) = (/ 60*dx1,-7*dx1*dx1*dx1,                              &
                                                120*(dx1+dx2),-8*(dx1*dx1*dx1 + dx2*dx2*dx2),             &
                                                60*dx2,-7*dx2*dx2*dx2 /)
                B( 2*ii-1 ) = 360*( -(this%y(ii) - this%y(ii-1))*idx1 + (this%y(ii+1) - this%y(ii))*idx2 )

                A( 2*ii  , 2*ii-3:2*ii+2 ) = (/ -6*idx1,dx1,                                          &
                                                6*(idx1+idx2),2*(dx1+dx2),                            &
                                                -6*idx2,dx2 /)
            end do
            dx1 = this%x(this%N) - this%x(this%N-1)
            A(2*this%N-1,2*this%N-3:2*this%N)   &
                                    = (/ -6.0d0,dx1*dx1,6.0d0,0.0d0 /)
            A(2*this%N,2*this%N)    = 1


        !---    For debugging purposes, here is the cubic spline fitting (commented)
        !             A = 0.0
        !             B = 0.0
        !             do ii = 1,2*this%N
        !                 A(ii,ii) = 1.0
        !             end do
        !             do ii = 2,this%N-1
        !                 dx1 = this%x(ii) - this%x(ii-1)
        !                 dx2 = this%x(ii+1) - this%x(ii)
        !                 idx1 = 1.0/dx1      !   note: have already checked dx1>0
        !                 idx2 = 1.0/dx2
        !                 A(2*ii-1,2*ii-3:2*ii+2 ) = (/ dx1,0.0,2*(dx1+dx2),0.0,dx2,0.0 /)
        !                 B(2*ii-1) = 6*( -(this%y(ii) - this%y(ii-1))*idx1 + (this%y(ii+1) - this%y(ii))*idx2 )
        !             end do
        !---

        !---    for debugging only, here is the matrix and vector. I think they're OK.
        !             do ii = 1,2*this%N
        !                 write (*,fmt='(1000f12.5)',advance="no") A(ii,:)
        !                 write (*,fmt='(a,f12.5)') "            ",B(ii)
        !             end do
        !---

            call DGESV( 2*this%N, NRHS, A, LDA, IPIV, B, LDB, INFO )
            if (INFO /= 0) then
                write (unit=0,fmt='(a,i6)') "Lib_QuinticSpline::refit - warning DGESV returned INFO=",INFO
            end if

            do ii = 1,this%N
                this%u(ii) = B(2*ii-1)
                this%v(ii) = B(2*ii)
            end do


            return
        end subroutine refit

        pure function splint(this,x) result(y)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      interpolate function
            type(quinticSpline),intent(in)          ::      this
            real(kind=8),intent(in)                         ::      x
            real(kind=8)                                    ::      y
            integer             ::      ii
            real(kind=8)                ::      aa,bb
            real(kind=8)                ::      dx1,dx2,idx1,idx2

            y = 0
            if (this%N == 0) return

            if (x < this%x(1)) then
                dx2 = this%x(2) - this%x(1)
                idx2 = 1.0/dx2  !   note: have checked dx2>0 in refit()
                aa = ( this%y(2) - this%y(1) )*idx2                             &       !   first deriv at x(1)
                   - (dx2/3.0) * ( this%u(1) + this%u(2)*0.5 )                  &
                   + (dx2*dx2*dx2/360.0) * ( 8*this%v(1) + 7*this%v(2) )
                bb = this%u(1)                                                          !   second deriv at x(1)
                dx2 = x - this%x(1)
                y = this%y(1) + dx2*(aa + 0.5*bb*dx2)
                return
            else if (x >= this%x(this%N)) then
                dx1 = this%x(this%N) - this%x(this%N-1)
                idx1 = 1.0/dx1  !   note: have checked dx1>0 in refit()
                aa = ( this%y(this%N) - this%y(this%N-1) )*idx1                 &       !   first deriv at x(N)
                   + (dx1/3.0) * ( this%u(this%N) + this%u(this%N-1)*0.5 )      &
                   - (dx1*dx1*dx1/360.0) * ( 8*this%v(this%N) + 7*this%v(this%N-1) )
                bb = this%u(this%N)                                                     !   second deriv at x(N)
                dx1 = x - this%x(this%N)
                y = this%y(this%N) + dx1*(aa + 0.5*bb*dx1)
                return
            else
                do ii = 1,this%N-1
                    if (x < this%x(ii+1)) exit
                end do
                !   now this%x(ii) <= x < this%x(ii+1)  and  1<=ii<N
                dx2 = this%x(ii+1) - this%x(ii)
                idx2 = 1.0/dx2
                aa = (this%x(ii+1) - x)*idx2
                bb = 1-aa
!                 print *,"ii,xx,aa,bb ",ii,x,aa,bb
                y  = ( aa*( 360.0*this%y(ii) + dx2*dx2*(60.0*(aa*aa-1)*this%u(ii)                               &
                                                        + dx2*dx2*(7+aa*aa*(-10+3*aa*aa))*this%v(ii)) )         &
                     + bb*( 360.0*this%y(ii+1) + dx2*dx2*(60.0*(bb*bb-1)*this%u(ii+1)                           &
                                                          + dx2*dx2*(7+bb*bb*(-10+3*bb*bb))*this%v(ii+1)) ) ) / 360.0
            end if

            return
        end function splint

        pure subroutine qsplint(this,x ,y,dy,d2y,d3y,d4y)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      interpolate function
            type(quinticSpline),intent(in)          ::      this
            real(kind=8),intent(in)                         ::      x
            real(kind=8),intent(out)                        ::      y
            real(kind=8),intent(out),optional               ::      dy
            real(kind=8),intent(out),optional               ::      d2y
            real(kind=8),intent(out),optional               ::      d3y
            real(kind=8),intent(out),optional               ::      d4y
            integer             ::      ii
            real(kind=8)                ::      aa,bb
            real(kind=8)                ::      dx1,dx2,idx1,idx2

            y = 0
            if (this%N == 0) return

            if (x < this%x(1)) then
                dx2 = this%x(2) - this%x(1)
                idx2 = 1.0/dx2  !   note: have checked dx2>0 in refit()
                aa = ( this%y(2) - this%y(1) )*idx2                             &       !   first deriv at x(1)
                   - (dx2/3.0) * ( this%u(1) + this%u(2)*0.5 )                  &
                   + (dx2*dx2*dx2/360.0) * ( 8*this%v(1) + 7*this%v(2) )
                bb = this%u(1)                                                          !   second deriv at x(1)
                dx2 = x - this%x(1)
                y = this%y(1) + dx2*(aa + 0.5*bb*dx2)
                if (present(dy)) dy = aa
                if (present(d2y)) d2y = bb
                if (present(d3y)) d3y = 0.0
                if (present(d4y)) d4y = 0.0
                return
            else if (x >= this%x(this%N)) then
                dx1 = this%x(this%N) - this%x(this%N-1)
                idx1 = 1.0/dx1  !   note: have checked dx1>0 in refit()
                aa = ( this%y(this%N) - this%y(this%N-1) )*idx1                 &       !   first deriv at x(N)
                   + (dx1/3.0) * ( this%u(this%N) + this%u(this%N-1)*0.5 )      &
                   - (dx1*dx1*dx1/360.0) * ( 8*this%v(this%N) + 7*this%v(this%N-1) )
                bb = this%u(this%N)                                                     !   second deriv at x(N)
                dx1 = x - this%x(this%N)
                y = this%y(this%N) + dx1*(aa + 0.5*bb*dx1)
                if (present(dy)) dy = aa
                if (present(d2y)) d2y = bb
                if (present(d3y)) d3y = 0.0
                if (present(d4y)) d4y = 0.0
                return
            else
                do ii = 1,this%N-1
                    if (x < this%x(ii+1)) exit
                end do
                !   now this%x(ii) <= x < this%x(ii+1)  and  1<=ii<N
                dx2 = this%x(ii+1) - this%x(ii)
                idx2 = 1.0/dx2
                aa = (this%x(ii+1) - x)*idx2
                bb = 1-aa
!                 print *,"ii,xx,aa,bb ",ii,x,aa,bb
                y  = ( aa*( 360.0*this%y(ii) + dx2*dx2*(60.0*(aa*aa-1)*this%u(ii)                               &
                                                        + dx2*dx2*(7+aa*aa*(-10+3*aa*aa))*this%v(ii)) )         &
                     + bb*( 360.0*this%y(ii+1) + dx2*dx2*(60.0*(bb*bb-1)*this%u(ii+1)                           &
                                                          + dx2*dx2*(7+bb*bb*(-10+3*bb*bb))*this%v(ii+1)) ) ) / 360.0
                if (present(dy)) then
                    dy  = ( -( 360.0*idx2*this%y(ii) + dx2*(60.0*(3*aa*aa-1)*this%u(ii)                               &
                                                        + dx2*dx2*(7+aa*aa*(-30+15*aa*aa))*this%v(ii)) )         &
                            +( 360.0*idx2*this%y(ii+1) + dx2*(60.0*(3*bb*bb-1)*this%u(ii+1)                           &
                                                          + dx2*dx2*(7+bb*bb*(-30+15*bb*bb))*this%v(ii+1)) ) ) / 360.0

                end if
                if (present(d2y)) then
                    d2y = (  ( 6*aa*this%u(ii)                              &
                             + dx2*dx2*(aa*(aa*aa-1))*this%v(ii))           &
                            +( 6*bb*this%u(ii+1)                            &
                             + dx2*dx2*(bb*(bb*bb-1))*this%v(ii+1)) ) / 6.0
                end if
                if (present(d3y)) then
                    d3y = ( -( 6*idx2*this%u(ii)                            &
                             + dx2*(3*aa*aa-1)*this%v(ii) )                 &
                            +( 6*idx2*this%u(ii+1)                          &
                             + dx2*(3*bb*bb-1)*this%v(ii+1) ) ) / 6.0
                end if
                if (present(d4y)) then
                    d4y = ( aa*this%v(ii) + bb*this%v(ii+1) )
                end if
            end if

            return
        end subroutine qsplint


!-------

        subroutine delete0(this,scrub)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      deallocate dynamically allocated memory.
    !*      note that this%x and this%y are allocated externally to this module
    !*      and will only be deleted if scrub = .true.
            type(quinticSpline),intent(inout)       ::      this
            logical,intent(in),optional             ::      scrub
            if (this%N == 0) return
            deallocate(this%u)
            deallocate(this%v)
            if (present(scrub)) then
                if (scrub) then
                    deallocate(this%x)
                    deallocate(this%y)
                end if
            end if
            this%N = 0
            return
        end subroutine delete0

        subroutine report0( this,u )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^
            type(quinticSpline),intent(in)          ::      this
            integer,intent(in),optional             ::      u
            integer             ::      uu
            integer         ::      ii
            uu = 6
            if(present(u)) uu = u
            write (unit=uu,fmt='(a,i6)') "quinticSpline N = ",this%N
            write (unit=uu,fmt='(a6,4a16)') "knot","x","y","y""","y"""""
            do ii = 1,this%N
                write (unit=uu,fmt='(i6,4f16.8)') ii,this%x(ii),this%y(ii),this%u(ii),this%v(ii)
            end do
            return
        end subroutine report0


    end module Lib_QuinticSpline


!     program testLib_QuinticSpline
! !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
!         use Lib_QuinticSpline
!         implicit none
!
!         integer,parameter           ::      N = 20
!
!         integer                 ::      ii
!         real(kind=8),dimension(N)       ::      xx,yy
!         real(kind=8)                    ::      xxxx,yyyy,dy,d2y,d3y,d4y
!         type(quinticSpline)     ::      q
!
!         print *,""
!         print *,"quinticSpline test program"
!         print *,""
!         do ii = 1,N
!            xxxx = (ii-1)*2.0*3.141592654/N
!            xx(ii) = xxxx
!            yy(ii) = cos( xxxx )
!         end do
!
!         q = quinticSpline_ctor( xx,yy )
!         call report(q)
!         print *,""
!
!         write (*,fmt='(8a16)') "theta","cos(theta)","-sin(theta)","y","dy","d2y","d3y","d4y"
!         do ii = -10,N*10+11
!             xxxx = (ii-1)*2.0*3.141592654/(N*10)
!             yyyy = splint( q,xxxx )
!             call qsplint( q,xxxx, yyyy,dy,d2y,d3y,d4y )
!             write (*,fmt='(8f16.8)') xxxx,cos( xxxx ),-sin( xxxx ),yyyy,dy,d2y,d3y,d4y
!         end do
!
!
!
!         call delete(q)
!         print *,""
!         print *,"done"
!         print *,""
!
!     end program testLib_QuinticSpline
